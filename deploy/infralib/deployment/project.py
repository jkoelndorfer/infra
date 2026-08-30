"""
infralib/deployment/project -- Infrastructure Projects
======================================================

This module contains the definition for a standard infralib project.

Projects define what to deploy. A project can be deployed into one or
more stacks.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, NewType, Type

from ..error import (
    DuplicateProjectError,
    InvalidDeploymentTargetError,
    InvalidInfrastructureNameError,
    NoSuchProjectError,
)
from ..pulumi.name import is_project_name
from .context import DeploymentContext
from .target import DeploymentTarget
from .stack import InfrastructureStack


InfrastructureProjectName = NewType("InfrastructureProjectName", str)

_all_projects: dict[str, Type["InfrastructureProject"]] = dict()


def all_projects(
    include_state_only: bool = False,
) -> list[Type["InfrastructureProject"]]:
    """
    Returns a list of all InfrastructureProjects.
    """
    return [p for p in _all_projects.values() if not p.state_only or include_state_only]


def get_project(
    name: str | InfrastructureProjectName,
    include_state_only: bool = False,
) -> Type["InfrastructureProject"]:
    """
    Returns the project with the given name.
    """
    try:
        project = _all_projects[name]
    except KeyError:
        raise NoSuchProjectError(name)

    if project.state_only and not include_state_only:
        raise NoSuchProjectError(name)

    return project


def project_name(name: str) -> InfrastructureProjectName:
    """
    Returns a new InfrastructureProjectName, ensuring that project name requirements
    are adhered to.
    """
    if not is_project_name(name):
        raise InvalidInfrastructureNameError(name, "InfrastructureProject")

    return InfrastructureProjectName(name)


class InfrastructureProject(ABC):
    """
    Defines the standard interface for an infrastructure project. This roughly corresponds to
    a Pulumi project [1].

    All infrastructure projects defined in this repository should conform to this standard.

    [1]: https://www.pulumi.com/docs/iac/concepts/projects/
    """

    # The name of the InfrastructureProject. This name must adhere to Pulumi requirements.
    name: ClassVar[str]

    # If True, this project is a state-only project. The project is not defined in code.
    state_only: bool = False

    def __init__(self, dctx: DeploymentContext) -> None:
        self.dctx = dctx

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        super().__init_subclass__(*args, **kwargs)
        defined_project_name = getattr(cls, "name", None)
        if defined_project_name is None:
            raise InvalidInfrastructureNameError("(none)", "InfrastructureProject")

        if _all_projects.get(cls.name, None) is not None:
            raise DuplicateProjectError(cls.name)

        _all_projects[cls.name] = cls
        # Cast project_name to InfrastructureProjectName to check validity.
        project_name(defined_project_name)

    @classmethod
    @abstractmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        """
        Returns a list of dependencies for this project with the given deployment target.

        Only direct dependencies should be specified by implementers.
        """

    @classmethod
    @abstractmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        """
        Returns a list of valid deployment targets for this infrastructure project.
        """

    @abstractmethod
    def pulumi_program(self) -> None:
        """
        The Pulumi program that defines this infrastructure project.
        """

    @classmethod
    def stack(cls, target: DeploymentTarget) -> InfrastructureStack:
        """
        Helper factory to create InfrastructureStacks for this project.
        """
        if target not in cls.deployment_targets():
            raise InvalidDeploymentTargetError(cls.name, target)
        return InfrastructureStack(cls, target)
