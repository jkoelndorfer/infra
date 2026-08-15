"""
infralib/pulumi/component -- Pulumi Infrastructure Component
============================================================

This module contains the definition for a Pulumi infrastructure component.
"""

from abc import abstractmethod
from typing import Any, TypeVar

from pulumi import ComponentResource, Inputs, ResourceOptions

from ..deployment.context import DeploymentContext

ArgT = TypeVar("ArgT")


class InfrastructureComponent[ArgT](ComponentResource):
    """
    An InfrastrutureComponent is a wrapper for Pulumi's ComponentResource.

    It functions nearly identically, but exposes the deployment context,
    provides a default set of resource options, and enhances the functionality
    of register_outputs.
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

        self.provision()

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
        Registers outputs for this InfrastructureComponent.

        Each registered output is set as an attribute on this object so that
        it can be accessed programatically.
        """
        for k, v in outputs.items():
            setattr(self, k, v)

        super().register_outputs(outputs)
