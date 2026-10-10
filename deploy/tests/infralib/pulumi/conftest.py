"""
tests/infralib/pulumi/conftest -- Pulumi Common Test Fixtures
=============================================================

This file contains common test fixtures for Pulumi tests.
"""

import asyncio
from typing import Any, Generator

import pulumi
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
from infralib.pulumi.provider import (
    KubernetesClientModule,
    ProviderFactory,
)


class NoopPulumiRuntimeMock(pulumi.runtime.Mocks):
    def new_resource(
        self, args: pulumi.runtime.MockResourceArgs
    ) -> tuple[str, dict[str, Any]]:
        return ("", {})

    def call(self, args: pulumi.runtime.MockCallArgs) -> tuple[dict[str, Any], None]:
        return ({}, None)


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

    def kubernetes_client(
        self,
    ) -> KubernetesClientModule:
        """
        Returns no Kubernetes client.
        """
        raise NotImplementedError(
            "CommandOnlyProviderFactory cannot create Kubernetes clients"
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
def noop_pulumi_runtime_mock() -> Generator[NoopPulumiRuntimeMock]:
    """
    Returns a Pulumi runtime mock that does nothing.

    See https://www.pulumi.com/docs/iac/guides/testing/unit/.
    """
    # As of Python 3.14, asyncio.get_event_loop() no longer implicitly
    # creates an event loop. Instead, it raises a RuntimeError. As of
    # this writing (Pulumi version 3.265.0), Pulumi does not properly
    # create an event loop when a runtime mock is set. We need to do
    # it ourselves.
    #
    # TODO: Remove this once Pulumi is updated to properly support
    # Python 3.14.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    m = NoopPulumiRuntimeMock()
    pulumi.runtime.set_mocks(m)

    yield m

    pending_tasks = asyncio.all_tasks(loop)
    if pending_tasks:
        loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))

    pulumi.runtime.settings.reset_options()
    asyncio.set_event_loop(None)
    loop.close()


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
        lambda dctx: command_only_provider_factory,
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
        provider_factory_factory=lambda dctx: command_only_provider_factory,
        project_kwargs=project_kwargs,
    )

    yield tools

    tools.cleanup()
