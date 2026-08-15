"""
infralib/pulumi/component -- Pulumi Infrastructure Component
============================================================

This module contains the definition for a Pulumi infrastructure component.
"""

from abc import abstractmethod
from typing import Any, TypeVar

from pulumi import ComponentResource, Inputs, Output, ResourceOptions

from ..error import InvalidRegisterOutputsCallError
from ..deployment.context import DeploymentContext

ArgT = TypeVar("ArgT")
OutputT = TypeVar("OutputT")


class RegisteredOutput[OutputT]:
    """
    A RegisteredOutput is used to track outputs that have been declared while
    provisioning an InfrastructureComponent.
    """

    def __init__(self, name: str, value: Output[OutputT]) -> None:
        self.name = name
        self.value = value


class InfrastructureComponent[ArgT](ComponentResource):
    """
    An InfrastrutureComponent is a wrapper for Pulumi's ComponentResource.

    It functions nearly identically, but exposes the deployment context and
    provides a default set of resource options.

    Do not call register_outputs. Instead, call output or output_resource to
    declare outputs. The register_outputs function will be called after
    provision().
    """

    def __init__(
        self, name: str, args: ArgT, opts: ResourceOptions, dctx: DeploymentContext
    ) -> None:
        super().__init__(
            f"InfrastructureComponent:index:{self.__class__.__name__}", name, {}, opts
        )
        self.args = args
        self.opts = opts
        self.dctx = dctx
        self.default_ropts = opts.merge(ResourceOptions(parent=self))
        self._outputs: list[RegisteredOutput[Any]] = list()

        self.provision()
        self._finalize_outputs()

    _pulumi_ro = ComponentResource.register_outputs

    def _finalize_outputs(self) -> None:
        """
        Finalizes outputs registered during provision(). Calls Pulumi's
        register_outputs() function to signal that the component has finished
        provisioning and provide the outputs to Pulumi's engine.
        """
        self._pulumi_ro({o.name: o.value for o in self._outputs})

    def output(self, name: str, v: Output[OutputT]) -> None:
        """
        Registers the value as an output for this component.

        This function can be called multiple times, at any time during provision().
        """
        setattr(self, name, v)
        self._outputs.append(RegisteredOutput(name, v))

    def output_resource(
        self,
        name: str,
        resource: Output[OutputT],
        attrs: list[str],
    ) -> None:
        """
        Registers the resource as an output for this component. The attributes
        given in attrs will be exported.

        This function can be called multiple times, at any time during provision().
        """
        return self.output(
            name,
            Output.from_input({k: getattr(resource, k) for k in attrs}),
        )

    @abstractmethod
    def provision(self) -> None:
        """
        Provisions resources and registers outputs for the InfrastructureComponent.

        This is called implicitly by the constructor.
        """
        raise NotImplementedError(
            "InfrastructureComponent subclasses must implement provision()"
        )

    def register_outputs(self, outputs: Inputs) -> None:
        """
        Calling register_outputs on an InfrastructureComponent is invalid.

        Call output or output_resource as needed, instead.
        """
        raise InvalidRegisterOutputsCallError()
