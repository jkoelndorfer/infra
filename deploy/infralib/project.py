"""
infralib/project -- Infrastructure Projects
===========================================

This module contains the definition for a standard infralib project and
associated classes.
"""

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Tuple

from .context import Environment, InfrastructureContext

InfrastructureStackInstance = Optional[str]
InfrastructureStackConfig = Tuple[Environment, Optional[str]]


class InfrastructureStack:
    """
    An infrastructure deployment. This roughly corresponds to a Pulumi stack [1].

    [1]: https://www.pulumi.com/docs/iac/concepts/stacks/
    """

    def __init__(
        self,
        project: "InfrastructureProject",
        environment: Environment,
        instance: InfrastructureStackInstance = None,
    ) -> None:
        self.project = project

        # The environment that the stack is deployed in.
        self.environment = environment

        # The name of the "instance" of the project. This might be a cloud provider region or a
        # feature branch name.
        self.instance = instance

    @property
    def name(self) -> str:
        """
        The name used to refer to this InfrastructureStack as a dependency.
        """
        return str(self)

    def __eq__(self, other: Any) -> bool:
        """
        Returns True if the other object is an InfrastructureStack that matches this one.
        """
        if not isinstance(other, self.__class__):
            return False

        return (
            self.project.name == other.project.name
            and self.environment == other.environment
            and self.instance == other.instance
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{str(self)}"

    def __str__(self) -> str:
        """
        Returns the string representation of the InfrastructureStack in Pulumi's expected format.
        """
        if self.instance is not None:
            stack_name = f"{self.environment}-{self.instance}"
        else:
            stack_name = self.environment

        return f"organization/{self.project.name}/{stack_name}"


class InfrastructureProject(ABC):
    """
    Defines the standard interface for an infrastructure project. This roughly corresponds to
    a Pulumi project [2].

    All infrastructure projects defined in this repository should conform to this standard.

    [2]: https://www.pulumi.com/docs/iac/concepts/projects/
    """

    # The name of the infrastructure (Pulumi) project.
    #
    # This project name must be compliant with Pulumi requirements. See
    # https://github.com/pulumi/pulumi/issues/1316#issue-320006753.
    name: str
    dependencies: list[InfrastructureStack]

    @abstractmethod
    def pulumi_program(self, context: InfrastructureContext) -> None:
        """
        The Pulumi program that defines this infrastructure project.
        """

    def stacks(self) -> Mapping[str, InfrastructureStack]:
        """
        Returns the set of valid InfrastructureStacks for this project.

        The key is the name of the InfrastructureStack.

        Subclasses should not override this method. Implement _stack_configs instead.
        """

    @abstractmethod
    def _stack_configs(self) -> list[InfrastructureStackConfig]:
        """
        A list of partial infrastructure stack configurations. Projects specify their valid
        InfrastructureStacks using this method.
        """

    def _stack(
        self, environment: Environment, instance: InfrastructureStackInstance
    ) -> InfrastructureStack:
        """
        Helper factory to create InfrastructureStacks for this project.
        """
        return InfrastructureStack(self, environment, instance)
