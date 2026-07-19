"""
projects.noop
=============

This module contains an InfrastructureProject that does nothing.

It is used for testing and as a basic example.
"""

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)


class NoopProject(InfrastructureProject):
    """
    Infrastructure project that does nothing. It serves as a minimal example project and one
    that can be used non-destructively for testing.
    """

    name = "noop"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(e, None) for e in [Environment.DEV, Environment.PROD]]

    def pulumi_program(self) -> None:
        """
        This project does not deploy any infrastructure. It only serves as a minimal example.

        To deploy infrastructure, instantiate a Pulumi provider and declare resources within
        a project's pulumi_program method in the same way as you normally would with Pulumi.
        """
