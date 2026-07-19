"""
infralib/deployment/target -- Deployment Targets
================================================

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

    # Test is used only during test runs (i.e. pytest).
    TEST = "test"


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
        Returns a new copy of this DeploymentTarget with the specified environment.
        """
        return DeploymentTarget(environment, self.region)

    def with_region(self, region: Optional[str]) -> DeploymentTarget:
        """
        Returns a new copy of this DeploymentTarget with the specified region.
        """
        return DeploymentTarget(self.environment, region)

    def __eq__(self, other: Any) -> bool:
        """
        Returns True if this DeploymentTarget is equivalent to other; False otherwise.
        """
        if not isinstance(other, self.__class__):
            return False

        return self.environment == other.environment and self.region == other.region

    def __hash__(self) -> int:
        return hash((self.environment, self.region))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(environment={self.environment}, region={self.region})"
