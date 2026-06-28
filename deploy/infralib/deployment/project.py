"""
infralib/deployment/project -- Infrastructure Projects
=====================================================

This module contains the definition for a standard infralib project.

Projects define what to deploy. A project can be deployed into one or
more stacks.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, NewType, TYPE_CHECKING

from ..config import InfrastructureConfiguration
from ..pulumi.name import is_project_name
from .target import DeploymentTarget

if TYPE_CHECKING:
    from .stack import InfrastructureStack


InfrastructureProjectName = NewType("InfrastructureProjectName", str)


def project_name(name: str) -> InfrastructureProjectName:
    """
    Returns a new InfrastructureProjectName, ensuring that project name requirements
    are adhered to.

    """
    if not is_project_name(name):
        raise ValueError("invalid infrastructure project name")

    return InfrastructureProjectName(name)


class InfrastructureProject(ABC):
    """
    Defines the standard interface for an infrastructure project. This roughly corresponds to
    a Pulumi project [1].

    All infrastructure projects defined in this repository should conform to this standard.

    [1]: https://www.pulumi.com/docs/iac/concepts/projects/
    """

    # The name of the InfrastructureProject. This name must adhere to Pulumi requirements.
    name: ClassVar[InfrastructureProjectName]

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        super().__init_subclass__(*args, **kwargs)
        project_name = getattr(cls, "name", None)
        if project_name is None:
            raise TypeError(f"{cls.__name__} must define a 'name' class variable")

        # Cast project_name to InfrastructureProjectName to check validity.
        _ = InfrastructureProjectName(project_name)

    @classmethod
    @abstractmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        """
        Returns a list of dependencies for this project in the given context.
        """

    @abstractmethod
    def pulumi_program(
        self, stack: InfrastructureStack, config: InfrastructureConfiguration
    ) -> None:
        """
        The Pulumi program that defines this infrastructure project.
        """

    @classmethod
    @abstractmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        """
        Returns a list of valid deployment targets for this infrastructure project.
        """

    @classmethod
    def stack(cls, target: DeploymentTarget) -> InfrastructureStack:
        """
        Helper factory to create InfrastructureStacks for this project.
        """
        if target not in cls.deployment_targets():
            raise ValueError(
                f"invalid deployment target {target} for project {cls.name}"
            )
        return InfrastructureStack(cls, target)
