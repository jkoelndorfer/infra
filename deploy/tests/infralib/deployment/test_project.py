"""
tests/infralib/deployment/test_project -- Infrastructure Project Tests
======================================================================

This file contains code to test infrastructure projects.
"""

from typing import Type

import pytest

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
    all_projects,
    get_project,
    project_name,
)
from infralib.error import (
    DuplicateProjectError,
    InvalidDeploymentTargetError,
    InvalidInfrastructureNameError,
    NoSuchProjectError,
)


class AlphaProject(InfrastructureProject):
    """
    First-tier InfrastructureProject used for testing.
    """

    name = "alpha"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.TEST, None),
        ]

    def pulumi_program(self) -> None:
        pass


class BetaProject(InfrastructureProject):
    """
    Second-tier InfrastructureProject used for testing.
    """

    name = "beta"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [AlphaProject.stack(DeploymentTarget(target.environment, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.TEST, "us-west-2"),
        ]

    def pulumi_program(self) -> None:
        pass


class TestProjectName:
    """
    Contains tests for the project_name function.
    """

    @pytest.mark.parametrize(
        "name", ["noop", "aws.bootstrap", ("MaxLength" * 100)[:100]]
    )
    def test_valid_project_name(self, name: str) -> None:
        """
        Tests that valid project names are returned as-is.
        """
        actual = project_name(name)

        assert actual == name

    @pytest.mark.parametrize(
        "name", ["InvalidAt@us-east-1", "TooLong" * 100, "Slashes/Not/Permitted"]
    )
    def test_invalid_project_name(self, name: str) -> None:
        """
        Tests that invalid project names raise an InvalidInfrastructureNameError.
        """
        with pytest.raises(InvalidInfrastructureNameError):
            project_name(name)


class TestProjectLookup:
    """
    Contains tests for project lookup functions.
    """

    def test_get_project(self) -> None:
        """
        Tests that get_project returns the expected project.
        """
        assert get_project("alpha").name == "alpha"

    def test_get_no_such_project(self) -> None:
        """
        Tests that get_project raises a NoSuchProjectError when no project with the
        given name is defined.
        """
        with pytest.raises(NoSuchProjectError):
            get_project("NonexistentProject")

    def test_all_projects(self) -> None:
        """
        Tests that all_projects returns all expected projects.
        """
        proj_names = [p.name for p in all_projects()]

        assert "alpha" in proj_names
        assert "beta" in proj_names


class TestInfrastructureProject:
    """
    Contains tests for the InfrastructureProject class.
    """

    def test_duplicate_project_raises_error(self) -> None:
        """
        Tests that declaring multiple InfrastructureProjects with the same name
        raises a DuplicateProjectError.
        """
        with pytest.raises(DuplicateProjectError):

            class DuplicatedProjectOne(InfrastructureProject):
                name = "duplicate"

                @classmethod
                def dependencies(
                    cls, target: DeploymentTarget
                ) -> list[InfrastructureStack]:
                    return []

                @classmethod
                def deployment_targets(cls) -> list[DeploymentTarget]:
                    return []

                def pulumi_program(self) -> None:
                    pass

            class DuplicatedProjectTwo(InfrastructureProject):
                name = "duplicate"

                @classmethod
                def dependencies(
                    cls, target: DeploymentTarget
                ) -> list[InfrastructureStack]:
                    return []

                @classmethod
                def deployment_targets(cls) -> list[DeploymentTarget]:
                    return []

                def pulumi_program(self) -> None:
                    pass

    @pytest.mark.parametrize(
        "project, target",
        [
            (AlphaProject, DeploymentTarget(Environment.DEV, None)),
            (AlphaProject, DeploymentTarget(Environment.DEV, "us-west-2")),
            (AlphaProject, DeploymentTarget(Environment.TEST, "us-west-2")),
            (BetaProject, DeploymentTarget(Environment.TEST, None)),
        ],
    )
    def test_stack_invalid_deployment_target(
        self, project: Type[InfrastructureProject], target: DeploymentTarget
    ) -> None:
        """
        Tests that calling stack() with an invalid deployment target raises an
        InvalidDeploymentTargetError.
        """
        with pytest.raises(InvalidDeploymentTargetError):
            project.stack(target)

    @pytest.mark.parametrize(
        "project_name",
        [
            "NotAName@",
            "Invalid/Project/Name",
            "TooLong" * 100,
        ],
    )
    def test_invalid_project_name(self, project_name: str) -> None:
        """
        Tests that creating a project with an invalid name raises an InvalidInfrastructureNameError.
        """
        with pytest.raises(InvalidInfrastructureNameError):

            class InvalidNamedProject(InfrastructureProject):
                name = project_name

                @classmethod
                def dependencies(
                    cls, target: DeploymentTarget
                ) -> list[InfrastructureStack]:
                    return []

                @classmethod
                def deployment_targets(cls) -> list[DeploymentTarget]:
                    return []

                def pulumi_program(self) -> None:
                    pass

    def test_undefined_project_name(self) -> None:
        """
        Tests that creating a project with no name raises an InvalidInfrastructureNameError.
        """
        with pytest.raises(InvalidInfrastructureNameError):

            class UnnamedProject(InfrastructureProject):
                @classmethod
                def dependencies(
                    cls, target: DeploymentTarget
                ) -> list[InfrastructureStack]:
                    return []

                @classmethod
                def deployment_targets(cls) -> list[DeploymentTarget]:
                    return []

                def pulumi_program(self) -> None:
                    pass

    def test_stack_returns_stack(self) -> None:
        """
        Tests that stack() returns an appropriate InfrastructureStack.
        """
        target = DeploymentTarget(Environment.TEST, None)
        stack = AlphaProject.stack(target)

        assert stack.project.name == AlphaProject.name
        assert stack.target == target

    def test_stack_with_invalid_target_raises_error(self) -> None:
        """
        Tests that stack() raises an InvalidDeploymentTargetError when the
        deployment target is invalid for the project.
        """
        target = DeploymentTarget(Environment.TEST, "europe-west-1")

        with pytest.raises(InvalidDeploymentTargetError):
            AlphaProject.stack(target)
