"""
infralib/context/context -- Deployment Context
==============================================

This file defines infrastructure deployment context. Context provides
attributes about a deployment that may change, like the environment,
region, or configuration.
"""

from ..config import InfrastructureConfiguration
from .environment import Environment


class InfrastructureContext:
    """
    Provides contextual information about the infrastructure deployment.
    """

    def __init__(
        self, config: InfrastructureConfiguration, environment: Environment
    ) -> None:
        self.config = config
        self.environment = environment
