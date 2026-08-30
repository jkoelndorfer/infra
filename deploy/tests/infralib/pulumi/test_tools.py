"""
tests/infralib/pulumi/test_tools -- Pulumi Operator Tool Tests
==============================================================

This file contains code to test the Pulumi operator's tools.
"""

from typing import Generator, Type

from pulumi import automation as auto
import pytest

from infralib import (
    DeploymentContext,
    DeploymentTarget,
    Environment,
    InfrastructureConfiguration,
    InfrastructureProject,
    InfrastructureStack,
    ProviderFactory,
    PulumiOperatorTools,
)
from infralib.deployment.project import _all_projects
from infralib.error import (
    NoSuchProjectError,
    StateOnlyError,
)


@pytest.fixture
def state_only_project(
    pulumi_operator_tools: PulumiOperatorTools,
) -> Generator[Type[InfrastructureProject]]:
    """
    Returns an InfrastructureProject which exists only in state.

    PulumiOperatorTools.try_state_only_project() is called to manufacture this.
    """
    project_name = "TestPulumiOperatorTools.state.only"
    work_dir = pulumi_operator_tools.work_dir()
    auto.create_stack(
        stack_name=Environment.TEST,
        project_name=project_name,
        program=lambda: None,
        opts=auto.LocalWorkspaceOptions(
            project_settings=auto.ProjectSettings(
                name=project_name,
                runtime="python",
                backend=auto.ProjectBackend(
                    url=pulumi_operator_tools.backend_provider.pulumi_url(project_name),
                ),
            ),
            work_dir=work_dir.name,
        ),
    )

    project = pulumi_operator_tools.try_state_only_project(project_name)

    yield project

    del _all_projects[project.name]


@pytest.fixture
def state_only_stack(
    state_only_project: Type[InfrastructureProject],
) -> InfrastructureStack:
    """
    Returns an InfrastructureStack which exists only in state.
    """
    return InfrastructureStack(
        state_only_project, DeploymentTarget(Environment.TEST, None)
    )


class TestPulumiOperatorTools:
    """
    Contains tests for the PulumiOperatorTools class.
    """

    def test_try_state_only_project_lookup(
        self,
        state_only_project: Type[InfrastructureProject],
    ) -> None:
        """
        Tests that try_state_only_project looks up a project that
        exists in Pulumi's state backend.
        """
        assert state_only_project.name == "TestPulumiOperatorTools.state.only"
        assert state_only_project.state_only

    def test_try_state_only_project_lookup_not_in_state(
        self,
        pulumi_operator_tools: PulumiOperatorTools,
    ) -> None:
        """
        Tests that try_state_only_project raises a NoSuchProject error
        when a project does not exist in Pulumi's state backend.
        """

        with pytest.raises(NoSuchProjectError):
            pulumi_operator_tools.try_state_only_project("nonexistent.project")

    def test_state_only_project_dependencies_raises_error(
        self,
        state_only_project: Type[InfrastructureProject],
        state_only_stack: InfrastructureStack,
    ) -> None:
        """
        Tests that a state-only InfrastructureProject raises an error when
        dependencies() is called.
        """

        with pytest.raises(StateOnlyError):
            state_only_project.dependencies(state_only_stack.target)

    def test_state_only_project_deployment_targets(
        self,
        state_only_project: Type[InfrastructureProject],
        state_only_stack: InfrastructureStack,
    ) -> None:
        """
        Tests that a state-only InfrastructureProject returns the expected
        set of deployment targets when deployment_targets() is called.
        """

        assert state_only_project.deployment_targets() == [state_only_stack.target]

    def test_state_only_project_program_raises_error(
        self,
        command_only_provider_factory: ProviderFactory,
        test_infrastructure_configuration: InfrastructureConfiguration,
        state_only_project: Type[InfrastructureProject],
        state_only_stack: InfrastructureStack,
    ) -> None:
        dctx = DeploymentContext(
            state_only_stack.target,
            test_infrastructure_configuration,
            command_only_provider_factory,
            lambda _: {},
        )
        project = state_only_project(dctx)

        with pytest.raises(StateOnlyError):
            project.pulumi_program()
