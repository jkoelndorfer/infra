"""
infralib/deployment/target -- Deployment Targets
===============================================

This file defines infrastructure deployment target. Deployment targets
define attributes of a deployment such as the environment or cloud region
that infrastructure is deployed to.
"""

from enum import StrEnum

from typing import Any, Optional


class Environment(StrEnum):
    """
    An enumeration containing all deployable environments.
    """

    DEV = "dev"
    PROD = "prod"


class DeploymentTarget:
    """
    Provides information about the infrastructure deployment target.
    """

    def __init__(
        self,
        environment: Environment,
        region: Optional[str],
    ) -> None:
        self.environment = environment
        self.region = region

    def with_environment(self, environment: Environment) -> DeploymentTarget:
        """
        Returns a new copy of this DeploymentTarget with the environment set to the specified value.
        """
        return DeploymentTarget(environment, self.region)

    def without_region(self) -> DeploymentTarget:
        """
        Returns a new copy of this DeploymentTarget with the region unspecified.
        """
        return DeploymentTarget(self.environment, None)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return self.environment == other.environment and self.region == other.region

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.environment}, {self.region})"
