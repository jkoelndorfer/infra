"""
infralib/deployment/stack -- Infrastructure Stacks
=================================================

This module contains the definition for a standard infralib stack.

A stack is a deployment of a project to a deployment target.
"""

from typing import Any, NewType, Self, Type, TYPE_CHECKING

from ..error import InvalidInfrastructureNameError
from ..pulumi.name import is_stack_name
from .target import DeploymentTarget, Environment

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
        raise InvalidInfrastructureNameError(name, "InfrastructureStack")

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

    @classmethod
    def parse(
        cls,
        project: Type[InfrastructureProject],
        stack_name: str | InfrastructureStackName,
    ) -> Self:
        """
        Given an InfrastructureProject and a stack name, returns an
        InfrastructureStack with a matching project and DeploymentTarget.
        """
        parts = stack_name.split(".")
        environment = Environment(parts[0])

        if len(parts) >= 2:
            region = parts[1]
        else:
            region = None

        if len(parts) >= 3:
            raise InvalidInfrastructureNameError(stack_name, cls.__name__)

        target = DeploymentTarget(environment, region)

        return cls(project, target)

    @property
    def name(self) -> InfrastructureStackName:
        """
        The name used to refer to this InfrastructureStack as a dependency.
        """
        parts: list[str] = [self.target.environment]
        if self.target.region is not None:
            parts.append(self.target.region)

        return stack_name(".".join(parts))

    def dependencies(self) -> list[InfrastructureStack]:
        """
        Return a list of direct dependencies for this stack.
        """
        return self.project.dependencies(self.target)

    @property
    def full_name(self) -> str:
        """
        Returns the full name of this InfrastructureStack.
        """
        return f"{self.project.name}/{self.name}"

    def __eq__(self, other: Any) -> bool:
        """
        Returns True if the other object is an InfrastructureStack that matches this one.
        """
        if not isinstance(other, self.__class__):
            return False

        return self.project.name == other.project.name and self.target == other.target

    def __hash__(self) -> int:
        return hash((self.project.name, hash(self.target)))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)})"

    def __str__(self) -> str:
        """
        Returns the string representation of the InfrastructureStack in Pulumi's expected format.
        """
        return self.full_name
