"""
infralib/project -- Infrastructure Projects
===========================================

This module contains the definition for a standard infralib project and
associated classes.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Mapping, NewType, Type, Self

from .config import InfrastructureConfiguration
from .target import DeploymentTarget
from .pulumi.name import is_project_name, is_stack_name


InfrastructureProjectName = NewType("InfrastructureProjectName", str)
InfrastructureStackName = NewType("InfrastructureStackName", str)


def project_name(name: str) -> InfrastructureProjectName:
    """
    Returns a new InfrastructureProjectName, ensuring that project name requirements
    are adhered to.

    """
    if not is_project_name(name):
        raise ValueError("invalid infrastructure project name")

    return InfrastructureProjectName(name)


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


class InfrastructureStack[P: "InfrastructureProject"]:
    """
    An infrastructure deployment. This roughly corresponds to a Pulumi stack [1].

    [1]: https://www.pulumi.com/docs/iac/concepts/stacks/
    """

    def __init__(
        self,
        project: Type[P],
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
        if self.target.instance is not None:
            stack_name = f"{self.target.environment}.{self.target.instance}"
        else:
            stack_name = self.target.environment

        return InfrastructureStackName(stack_name)

    def __eq__(self, other: Any) -> bool:
        """
        Returns True if the other object is an InfrastructureStack that matches this one.
        """
        if not isinstance(other, self.__class__):
            return False

        return (
            self.project.name == other.project.name
            and self.target.environment == other.target.environment
            and self.target.instance == other.target.instance
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{str(self)}"

    def __str__(self) -> str:
        """
        Returns the string representation of the InfrastructureStack in Pulumi's expected format.
        """
        return f"organization/{self.project.name}/{stack_name}"


class InfrastructureProject(ABC):
    """
    Defines the standard interface for an infrastructure project. This roughly corresponds to
    a Pulumi project [2].

    All infrastructure projects defined in this repository should conform to this standard.

    [2]: https://www.pulumi.com/docs/iac/concepts/projects/
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
    def dependencies(
        cls, target: DeploymentTarget
    ) -> list[InfrastructureStack["InfrastructureProject"]]:
        """
        Returns a list of dependencies for this project in the given context.
        """

    @abstractmethod
    def pulumi_program(
        self, stack: InfrastructureStack[Self], config: InfrastructureConfiguration
    ) -> None:
        """
        The Pulumi program that defines this infrastructure project.
        """

    @classmethod
    def stacks(cls) -> Mapping[InfrastructureStackName, InfrastructureStack[Self]]:
        """
        Returns the set of valid InfrastructureStacks for this project.

        The key is the name of the InfrastructureStack.

        Subclasses should not override this method. Implement deployment_targets instead.
        """
        smap = dict()
        for target in cls.deployment_targets():
            s = cls.stack(target)
            smap[s.name] = s
        return smap

    @classmethod
    @abstractmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        """
        Returns a list of valid deployment targets for this infrastructure project.
        """

    @classmethod
    def stack(cls, target: DeploymentTarget) -> InfrastructureStack[Self]:
        """
        Helper factory to create InfrastructureStacks for this project.
        """
        if target not in cls.deployment_targets():
            raise ValueError(
                f"invalid deployment target {target} for project {cls.name}"
            )
        return InfrastructureStack(cls, target)
