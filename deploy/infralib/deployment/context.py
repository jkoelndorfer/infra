"""
infralib/deployment/project -- Infrastructure Deployment Context
================================================================

This module contains the definiton for an infralib deployment context.

A deployment context is provided to all instantiated infralib projects. It
provides access to global configuration and helpers.
"""

from typing import Any

from ..config import InfrastructureConfiguration
from ..pulumi.provider import ProviderFactory
from ..pulumi.types import StackOutputResolver
from .target import DeploymentTarget


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

        self._kv: dict[str, Any] = dict()

    def kv_set(self, key: str, value: Any) -> None:
        """
        Stores a value for the lifetime of this DeploymentContext.

        This can be used to persist objects that can only exist for a single Pulumi
        program run, like a provider.
        """
        self._kv[key] = value

    def kv_get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value previously set by kv_set.
        """
        return self._kv.get(key, default)
