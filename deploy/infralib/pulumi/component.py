"""
infralib/pulumi/component -- Pulumi Infrastructure Component
============================================================

This module contains the definition for a Pulumi infrastructure component.
"""

from abc import abstractmethod
from typing import Any, Callable, TypeVar

from pulumi import (
    ComponentResource,
    Input,
    Inputs,
    ResourceOptions,
)

from ..error import InvalidRegisterOutputsCallError
from ..deployment.context import DeploymentContext

ArgT = TypeVar("ArgT")
InputT = TypeVar("InputT")
RegisterOutputs = Callable[[ComponentResource, Inputs], None]


class RegisteredOutput[InputT]:
    """
    A RegisteredOutput is used to track outputs that have been declared while
    provisioning an InfrastructureComponent.
    """

    def __init__(self, name: str, value: Input[InputT]) -> None:
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
        self,
        name: str,
        args: ArgT,
        dctx: DeploymentContext,
        opts: ResourceOptions | None = None,
        pulumi_ro: RegisterOutputs = ComponentResource.register_outputs,
    ) -> None:
        super().__init__(
            f"InfrastructureComponent:index:{self.__class__.__name__}", name, {}, opts
        )
        self.name = name
        self.args = args
        self.opts = opts
        self.dctx = dctx
        self.default_ropts = ResourceOptions(parent=self)
        self._outputs: list[RegisteredOutput[Any]] = list()
        self._pulumi_ro = pulumi_ro

        self.provision()
        self._finalize_outputs()

    def _finalize_outputs(self) -> None:
        """
        Finalizes outputs registered during provision(). Calls Pulumi's
        register_outputs() function to signal that the component has finished
        provisioning and provide the outputs to Pulumi's engine.
        """
        self._pulumi_ro(self, {o.name: o.value for o in self._outputs})

    def output(
        self,
        name: str,
        v: Input[InputT],
    ) -> None:
        """
        Registers the value as an output for this component.

        This function can be called multiple times, at any time during provision().
        """
        self._outputs.append(RegisteredOutput(name, v))

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

        Call output as needed, instead.
        """
        raise InvalidRegisterOutputsCallError()
