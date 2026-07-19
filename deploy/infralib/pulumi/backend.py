"""
infralib/pulumi/backend -- Pulumi Backend Provider
==================================================

This module contains the definition for a Pulumi backend provider.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from ..error import InvalidLocalBackendError
from ..deployment.stack import InfrastructureStack


class BackendProvider(ABC):
    """
    A backend describes how to store state files.

    Typically, Pulumi backends are associated with a specific project. Projects defined via
    this library instead make use of common backends for consistency.
    """

    @abstractmethod
    def pulumi_url(self, stack: InfrastructureStack) -> str:
        """
        Returns the backend URL expected by Pulumi for this backend.

        See https://www.pulumi.com/docs/iac/operations/stack-management/using-a-diy-backend/.
        """


class LocalBackendProvider(BackendProvider):
    """
    A local backend stores state files locally.
    """

    SENTINEL_FILE_NAME = ".infralib-pulumi-local-backend"

    def __init__(self, path: Path) -> None:
        sentinel_file = path / self.SENTINEL_FILE_NAME

        if not sentinel_file.is_file():
            raise InvalidLocalBackendError(path, self.SENTINEL_FILE_NAME)

        self.path = path

    def pulumi_url(self, stack: InfrastructureStack) -> str:
        return f"file://{str(self.path.absolute())}"
