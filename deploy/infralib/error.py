"""
infralib/error -- Infralib Errors
=================================

This module contains definitions for infralib error types.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .deployment.target import DeploymentTarget
    from .deployment.stack import InfrastructureStack


class InfralibError(Exception):
    """
    Base class for all infralib errors.
    """


class CircularDependencyError(InfralibError):
    """
    Error raised when there is a circular dependency.
    """

    def __init__(self, dependency_chain: list[object]) -> None:
        self.dependency_chain = dependency_chain

        cycle = " -> ".join((str(d) for d in dependency_chain))
        super().__init__(f"circular dependency: {cycle}")


class DuplicateProjectError(InfralibError):
    """
    Error raised when multiple projects are discovered with the same name.
    """

    def __init__(self, project_name: str) -> None:
        self.project_name = project_name

        super().__init__(f"more than one project with name: {self.project_name}")


class NoSuchProjectError(InfralibError):
    """
    Error raised when a project with the given name cannot be found.
    """

    def __init__(self, project_name: str) -> None:
        self.project_name = project_name

        super().__init__(f"no such project: {self.project_name}")


class InvalidConfigurationError(InfralibError):
    """
    Error raised when configuration is invalid.
    """


class InvalidDeploymentTargetError(InfralibError):
    """
    Error raised when the deployment target selected for a project is invalid.
    """

    def __init__(self, project_name: str, deployment_target: DeploymentTarget) -> None:
        self.project_name = project_name
        self.deployment_target = deployment_target

        super().__init__(
            f"invalid deployment target for project {self.project_name}: {self.deployment_target}"
        )


class InvalidInfrastructureNameError(InfralibError):
    """
    Error raised when attempting to create an InfrastructureProjectName
    or InfrastructureStackName that is invalid.
    """

    def __init__(self, invalid_name: str, obj_type: str) -> None:
        self.invalid_name = invalid_name
        self.obj_type = obj_type

        super().__init__(f"invalid {obj_type}: {invalid_name}")


class InvalidLocalBackendError(InfralibError):
    """
    Error raised when the selected local backend directory is invalid.
    """

    def __init__(self, path: Path, sentinel_filename: str) -> None:
        self.path = path
        self.sentinel_filename = sentinel_filename

        super().__init__(
            f"invalid local backend path: {path}; missing sentinel file {sentinel_filename}"
        )


class UndeclaredDependencyError(InfralibError):
    """
    Error raised when a project tries to access outputs for a stack that is not
    declared as a dependency.
    """

    def __init__(
        self,
        requesting_stack: InfrastructureStack,
        outputting_stack: InfrastructureStack,
    ) -> None:
        self.requesting_stack = requesting_stack
        self.outputting_stack = outputting_stack

        super().__init__(
            f"{outputting_stack} is not a declared dependency of {requesting_stack}"
        )
