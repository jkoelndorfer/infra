"""
infralib/depoyment/stack -- Infrastructure Stacks
=================================================

This module contains the definition for a standard infralib stack.

A stack is a deployment of a project to a deployment target.
"""

from typing import Any, NewType, Type, TYPE_CHECKING

from ..pulumi.name import is_stack_name
from .target import DeploymentTarget

if TYPE_CHECKING:
    from .project import InfrastructureProject

InfrastructureStackName = NewType("InfrastructureStackName", str)


def stack_name(name: str) -> InfrastructureStackName:
    """
    Returns a new InfrastructureStackName, ensuring that stack name requirements
    are adhered to.

    Pulumi documentation describes stack name restrictions.

    https://www.pulumi.com/docs/iac/concepts/stacks/#create-stack
    """
    if not is_stack_name(name):
        raise ValueError("invalid infrastructure stack name")

    return InfrastructureStackName(name)


class InfrastructureStack:
    """
    An infrastructure deployment. This roughly corresponds to a Pulumi stack [1].

    [1]: https://www.pulumi.com/docs/iac/concepts/stacks/
    """

    def __init__(
        self,
        project: Type[InfrastructureProject],
        target: DeploymentTarget,
    ) -> None:
        # The infrastructure project deployed by this stack.
        self.project = project

        # The deployment target for the project.
        self.target = target

    @property
    def name(self) -> InfrastructureStackName:
        """
        The name used to refer to this InfrastructureStack as a dependency.
        """
        if self.target.region is not None:
            stack_name = f"{self.target.environment}.{self.target.region}"
        else:
            stack_name = self.target.environment

        return InfrastructureStackName(stack_name)

    @property
    def full_name(self) -> str:
        return f"organization/{self.project.name}/{self.name}"

    def __eq__(self, other: Any) -> bool:
        """
        Returns True if the other object is an InfrastructureStack that matches this one.
        """
        if not isinstance(other, self.__class__):
            return False

        return self.project.name == other.project.name and self.target == other.target

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{str(self)}"

    def __str__(self) -> str:
        """
        Returns the string representation of the InfrastructureStack in Pulumi's expected format.
        """
        return self.full_name
