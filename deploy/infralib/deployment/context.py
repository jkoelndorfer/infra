"""
infralib/deployment/project -- Infrastructure Deployment Context
================================================================

This module contains the definiton for an infralib deployment context.

A deployment context is provided to all instantiated infralib projects. It
provides access to global configuration and helpers.
"""

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
