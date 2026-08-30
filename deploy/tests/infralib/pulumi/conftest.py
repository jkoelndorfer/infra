"""
tests/infralib/pulumi/conftest -- Pulumi Common Test Fixtures
=============================================================

This file contains common test fixtures for Pulumi tests.
"""

from typing import Any, Generator

import pulumi_aws as aws
import pulumi_command as command
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s
import pytest

from infralib import (
    BackendProvider,
    DeploymentContext,
    DeploymentTarget,
    Environment,
    InfrastructureConfiguration,
    InfrastructureProject,
    InfrastructureStack,
    PulumiOperatorTools,
    StackOutputResolver,
)
from infralib.pulumi.provider import ProviderFactory


class CommandOnlyProviderFactory(ProviderFactory):
    """
    Provider factory that only returns command providers.
    """

    def aws_provider(
        self,
        name: str,
        assume_role_arn: str | None = None,
        region: str | None = None,
        profile: str | None = None,
    ) -> aws.Provider:
        """
        Returns no provider.
        """
        raise NotImplementedError(
            "CommandOnlyProviderFactory cannot create cloud Providers"
        )

    def command_provider(self, name: str = "command") -> command.Provider:
        """
        Returns a Command provider.
        """
        return command.Provider(name)

    def gcp_provider(self, name: str = "gcp") -> gcp.Provider:
        """
        Returns no provider.
        """
        raise NotImplementedError(
            "CommandOnlyProviderFactory cannot create cloud Providers"
        )

    def kubernetes_provider(
        self,
        name: str = "kubernetes",
        context: str | None = None,
    ) -> k8s.Provider:
        """
        Returns no provider.
        """
        raise NotImplementedError(
            "CommandOnlyProviderFactory cannot create cloud Providers"
        )


class NoopTestProject(InfrastructureProject):
    """
    InfrastructureProject that does nothing. It is used exclusively for testing.

    This project can be used in places where an InfrastructureProject (or stack,
    via stack()) are needed.
    """

    name = "noop.test.pulumi"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(Environment.TEST, None)]

    def pulumi_program(self) -> None:
        """
        Empty Pulumi program that does nothing. This project is used only for testing.
        """


@pytest.fixture
def command_only_provider_factory() -> CommandOnlyProviderFactory:
    """
    ProviderFactory that can only produce a Command provider.

    Attempting to create any other type of provider will result in an
    exception being raised.
    """
    return CommandOnlyProviderFactory()


@pytest.fixture
def test_deployment_target() -> DeploymentTarget:
    """
    DeploymentTarget suitable for use during test runs.
    """
    return DeploymentTarget(Environment.TEST, None)


@pytest.fixture
def noop_stack_output_resolver() -> StackOutputResolver:
    """
    StackOutputResolver that returns no outputs.
    """
    return lambda _: {}


@pytest.fixture
def test_deployment_context(
    test_deployment_target: DeploymentTarget,
    test_infrastructure_configuration: InfrastructureConfiguration,
    command_only_provider_factory: CommandOnlyProviderFactory,
    noop_stack_output_resolver: StackOutputResolver,
) -> DeploymentContext:
    """
    DeploymentContext suitable for use during test runs.
    """
    return DeploymentContext(
        test_deployment_target,
        test_infrastructure_configuration,
        command_only_provider_factory,
        noop_stack_output_resolver,
    )


@pytest.fixture
def noop_infrastructure_project(
    test_deployment_context: DeploymentContext,
) -> InfrastructureProject:
    """
    InfrastructureProject that does nothing. It cannot instantiate Pulumi
    providers or get stack outputs.
    """
    return NoopTestProject(test_deployment_context)


@pytest.fixture
def noop_infrastructure_stack(
    test_deployment_target: DeploymentTarget,
) -> InfrastructureStack:
    """
    InfrastructureStack for a project that does nothing.
    """
    return NoopTestProject.stack(test_deployment_target)


@pytest.fixture
def project_kwargs() -> dict[str, Any]:
    """
    Returns keyword arguments passed to InfrastructureProjects when
    they are instantiated.
    """
    return dict()


@pytest.fixture
def pulumi_operator_tools(
    test_infrastructure_configuration: InfrastructureConfiguration,
    local_backend_provider: BackendProvider,
    command_only_provider_factory: ProviderFactory,
    project_kwargs: dict[str, Any],
) -> Generator[PulumiOperatorTools]:
    """
    Returns a PulumiOperatorTools suitable for testing.
    """
    tools = PulumiOperatorTools(
        config=test_infrastructure_configuration,
        backend_provider=local_backend_provider,
        provider_factory=command_only_provider_factory,
        project_kwargs=project_kwargs,
    )

    yield tools

    tools.cleanup()
