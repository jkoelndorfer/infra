"""
infralib/deployment/project -- Infrastructure Deployment Context
================================================================

This module contains the definiton for an infralib deployment context.

A deployment context is provided to all instantiated infralib projects. It
provides access to global configuration and helpers.
"""

from typing import Any, Type, TYPE_CHECKING

from ..config import InfrastructureConfiguration
from ..pulumi.provider import ProviderFactory
from ..pulumi.types import StackOutputResolver
from .target import DeploymentTarget

if TYPE_CHECKING:
    from .project import InfrastructureProject

NO_DEFAULT = object()


class DeploymentContext:
    """
    Defines standard context provided to all infrastructure deployments.
    """

    def __init__(
        self,
        target: DeploymentTarget,
        config: InfrastructureConfiguration,
        provider_factory: ProviderFactory,
        outputs: StackOutputResolver,
    ) -> None:
        self.target = target
        self.config = config
        self.provider_factory = provider_factory
        self.outputs = outputs

        # This dictionary provides a cache that InfrastructureProjects can
        # use to persist data for a single Pulumi program run.
        self._project_run_cache: dict[str, Any] = dict()

    def kv_set(
        self, project: Type[InfrastructureProject], key: str, value: Any
    ) -> None:
        """
        Stores a value namespaced for the given InfrastructureProject.

        This can be used to persist objects that can only exist for a single Pulumi
        program run, like a provider.
        """
        c = self._project_run_cache.setdefault(project.name, dict())
        c[key] = value

    def kv_get(
        self, project: Type[InfrastructureProject], key: str, default: Any = NO_DEFAULT
    ) -> Any:
        """
        Retrieves a value previously set by kv_set.
        """
        proj_dict = self._project_run_cache.get(project.name, dict())
        if default is NO_DEFAULT:
            return proj_dict[key]
        else:
            return proj_dict.get(key, default)
