"""
tests/infralib/pulumi/test_operator -- Pulumi Operator Tests
============================================================

This file contains code to test the Pulumi operator.
"""

from pathlib import Path
from shlex import join as shjoin
from tempfile import TemporaryDirectory as RealTemporaryDirectory
from typing import Any, Callable, Generator, TYPE_CHECKING
from unittest.mock import call, Mock, patch

from pulumi import automation as auto, export, ResourceOptions
from pulumi_command import local
import pytest

from infralib import (
    DeploymentTarget,
    Environment,
    export_resource,
    InfrastructureProject,
    InfrastructureStack,
    PulumiOperator,
    PulumiOperatorTools,
)
from infralib.pulumi.operator.stack import PulumiStackDescription

if TYPE_CHECKING:
    TemporaryDirectory = RealTemporaryDirectory[str]
else:
    TemporaryDirectory = RealTemporaryDirectory


class LocalCommandProject(InfrastructureProject):
    """
    Project that uses command resources to make modifications
    to local temporary directories.
    """

    name = "test.integration.localcommand"

    def __init__(
        self,
        *args: Any,
        file_resource_path: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.file_resource_path = file_resource_path

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.TEST, None),
            # us-west-2 as a DeploymentTarget allows the DependerStack to take a
            # attempt looking up outputs against this target. Without it, an
            # InvalidDeploymentTargetError is raised (which is not the scenario
            # we'd like to test!)
            DeploymentTarget(Environment.TEST, "us-west-2"),
        ]

    def pulumi_program(self) -> None:
        cmd = self.dctx.provider_factory.command_provider()

        local.Command(
            "tempfile_cmd",
            create=shjoin(["touch", str(self.file_resource_path)]),
            delete=shjoin(["rm", "-f", str(self.file_resource_path)]),
            triggers=[
                str(self.file_resource_path),
            ],
            opts=ResourceOptions(provider=cmd),
        )
        stat_dev_null = local.Command(
            "stat_dev_null",
            create=shjoin(["stat", "--format=%s", "/dev/null"]),
            opts=ResourceOptions(provider=cmd),
        )

        export_resource(
            "stat_dev_null",
            stat_dev_null,
            ["stdout"],
        )
        export("tempfile", str(self.file_resource_path))


class DependerProject(InfrastructureProject):
    """
    Project that declares a dependency on the *one* DeploymentTarget of LocalCommandProject.

    The us-west-2 region is a valid target for both stacks, but this stack only declares
    a dependency on the regionless stack.
    """

    name = "test.integration.depender"

    def __init__(
        self,
        *args: Any,
        file_resource_path: Path,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [LocalCommandProject.stack(DeploymentTarget(Environment.TEST, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.TEST, None),
            DeploymentTarget(Environment.TEST, "us-west-2"),
        ]

    def pulumi_program(self) -> None:
        o = self.dctx.outputs(LocalCommandProject.stack(self.dctx.target)).get(
            "tempfile"
        )

        if o is None:
            return

        export("tempfile", o.value)


@pytest.fixture
def local_command_stack() -> InfrastructureStack:
    """
    Returns a stack for the LocalCommandProject.
    """
    return LocalCommandProject.stack(DeploymentTarget(Environment.TEST, None))


@pytest.fixture
def resource_directory() -> Generator[TemporaryDirectory]:
    """
    Yields a temporary directory that files can be created in for local Pulumi
    program testing.
    """
    dir = TemporaryDirectory(
        prefix="infralib-pulumi-operator-test-",
        ignore_cleanup_errors=True,
        delete=False,
    )

    yield dir

    dir.cleanup()


@pytest.fixture
def file_resource_path(resource_directory: TemporaryDirectory) -> Path:
    return Path(resource_directory.name) / "test_operator_testfile"


@pytest.fixture
def project_kwargs(
    file_resource_path: Path,
) -> dict[str, Any]:
    """
    Returns keyword arguments passed to InfrastructureProjects when
    they are instantiated.
    """
    return {
        "file_resource_path": file_resource_path,
    }


@pytest.fixture
def pulumi_operator(
    pulumi_operator_tools: PulumiOperatorTools,
) -> PulumiOperator:
    """
    Returns a PulumiOperator suitable for testing.
    """
    return PulumiOperator.new(pulumi_operator_tools)


class TestPulumiOperator:
    """
    Contains tests for the PulumiOperator class.
    """

    def test_list_stacks(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests listing stacks.
        """

        class StateOnlyProject(InfrastructureProject):
            """
            Test project that exists only in state.
            """

            name = "TestPulumiOperator.0.test_list_stacks.state.only"
            state_only = True

            def __init__(
                self,
                *args: Any,
                file_resource_path: Path,
                **kwargs: Any,
            ) -> None:
                super().__init__(*args, **kwargs)

            @classmethod
            def dependencies(
                cls, target: DeploymentTarget
            ) -> list[InfrastructureStack]:
                return []

            @classmethod
            def deployment_targets(cls) -> list[DeploymentTarget]:
                return [
                    DeploymentTarget(Environment.TEST, None),
                ]

            def pulumi_program(self) -> None: ...

        class CodeOnlyProject(InfrastructureProject):
            """
            Test project that exists only in code.
            """

            name = "TestPulumiOperator.1.test_list_stacks.code.only"

            def __init__(
                self,
                *args: Any,
                file_resource_path: Path,
                **kwargs: Any,
            ) -> None:
                super().__init__(*args, **kwargs)

            @classmethod
            def dependencies(
                cls, target: DeploymentTarget
            ) -> list[InfrastructureStack]:
                return []

            @classmethod
            def deployment_targets(cls) -> list[DeploymentTarget]:
                return [
                    DeploymentTarget(Environment.TEST, None),
                ]

            def pulumi_program(self) -> None: ...

        class CodeAndStateProject(InfrastructureProject):
            """
            Test project that exists in code and state.
            """

            name = "TestPulumiOperator.2.test_list_stacks.code.and.state"

            def __init__(
                self,
                *args: Any,
                file_resource_path: Path,
                **kwargs: Any,
            ) -> None:
                super().__init__(*args, **kwargs)

            @classmethod
            def dependencies(
                cls, target: DeploymentTarget
            ) -> list[InfrastructureStack]:
                return []

            @classmethod
            def deployment_targets(cls) -> list[DeploymentTarget]:
                return [
                    DeploymentTarget(Environment.TEST, None),
                ]

            def pulumi_program(self) -> None: ...

        target = DeploymentTarget(Environment.TEST, None)
        pulumi_operator.stack.up(StateOnlyProject.stack(target))
        pulumi_operator.stack.up(CodeAndStateProject.stack(target))

        projects = {
            StateOnlyProject.name: StateOnlyProject,
            CodeOnlyProject.name: CodeOnlyProject,
            CodeAndStateProject.name: CodeAndStateProject,
        }
        with patch("infralib.deployment.project._all_projects", projects):
            stack_list = pulumi_operator.stack.list()

        assert stack_list == [
            PulumiStackDescription(
                StateOnlyProject.stack(target),
                code=False,
                state=True,
            ),
            PulumiStackDescription(
                CodeOnlyProject.stack(target),
                code=True,
                state=False,
            ),
            PulumiStackDescription(
                CodeAndStateProject.stack(target),
                code=True,
                state=True,
            ),
        ]

    def test_local_command_project_up(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
        file_resource_path: Path,
    ) -> None:
        """
        Tests running `up` on a LocalCommandProject.
        """
        up_result = pulumi_operator.stack.up(local_command_stack)

        assert up_result.summary.result == "succeeded"
        assert file_resource_path.is_file()

        changes = up_result.summary.resource_changes
        assert changes is not None
        assert changes.get(auto.OpType.CREATE, 0) >= 2

        assert up_result.outputs["stat_dev_null"].value["stdout"] == "0"
        assert up_result.outputs["tempfile"].value == str(file_resource_path)

    def test_up_with_output_refresh(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests running `up` on a LocalCommandProject with output_refresh = True.
        """
        output_mock = Mock(spec=["__call__"])
        pulumi_operator.stack.up(
            local_command_stack,
            on_output=output_mock,
            on_error=output_mock,
            do_refresh=True,
            output_refresh=True,
        )

        output_mock.assert_has_calls([call("Refreshing (test):")])

    def test_local_command_project_up_twice(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests running `up` on a LocalCommandProject twice in a row.
        """
        pulumi_operator.stack.up(local_command_stack)
        second_up_result = pulumi_operator.stack.up(local_command_stack)

        assert second_up_result.summary.result == "succeeded"

        changes = second_up_result.summary.resource_changes
        assert changes is not None
        assert changes.get(auto.OpType.CREATE, 0) == 0

    def test_local_commmand_project_up_destroy(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
        file_resource_path: Path,
    ) -> None:
        """
        Tests running `up` on a LocalCommandProject, then `destroy`.
        """
        pulumi_operator.stack.up(local_command_stack)

        assert file_resource_path.is_file()

        pulumi_operator.stack.destroy(local_command_stack)

        assert not file_resource_path.is_file()

    def test_local_command_project_preview(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests running `preview` on a LocalCommandProject.
        """
        preview_result = pulumi_operator.stack.preview(local_command_stack)

        changes = preview_result.change_summary
        assert changes.get(auto.OpType.CREATE, 0) >= 2

    def test_project_workspace_discovers_stacks(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests that a project workspace discovers existing stacks.
        """
        ws = pulumi_operator.tools.pulumi_project_workspace(
            local_command_stack.project.name
        )
        pulumi_operator.stack.up(local_command_stack)

        existing_stacks = ws.list_stacks()

        assert len(existing_stacks) == 1
        assert existing_stacks[0].name == local_command_stack.name

    def test_project_workspace_uses_cache(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests that requesting a project workspace multiple times returns the
        same workspace.
        """
        project_name = local_command_stack.project.name

        ws_a = pulumi_operator.tools.pulumi_project_workspace(project_name)
        ws_b = pulumi_operator.tools.pulumi_project_workspace(project_name)

        assert ws_a is ws_b

    def test_shell(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests starting a shell for a stack.
        """
        pstack = pulumi_operator.tools.pulumi_stack(local_command_stack)
        testfile_path = Path("test_shell")
        full_path = Path(pstack.workspace.work_dir) / testfile_path

        pulumi_operator.stack.shell(local_command_stack, ["touch", "test_shell"])

        assert full_path.is_file()

    def test_stack_rename_cross_project(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests renaming a stack across projects.
        """

        class RenameTargetProject(InfrastructureProject):
            """
            Project that serves as a rename target.
            """

            name = "test.integration.renamed"

            def __init__(
                self,
                *args: Any,
                file_resource_path: Path,
                **kwargs: Any,
            ) -> None:
                super().__init__(*args, **kwargs)
                self.file_resource_path = file_resource_path

            @classmethod
            def dependencies(
                cls, target: DeploymentTarget
            ) -> list[InfrastructureStack]:
                return []

            @classmethod
            def deployment_targets(cls) -> list[DeploymentTarget]:
                return [
                    DeploymentTarget(Environment.TEST, None),
                    # us-west-2 as a DeploymentTarget allows the DependerStack to take a
                    # attempt looking up outputs against this target. Without it, an
                    # InvalidDeploymentTargetError is raised (which is not the scenario
                    # we'd like to test!)
                    DeploymentTarget(Environment.TEST, "us-west-2"),
                ]

            def pulumi_program(self) -> None: ...

        up_result = pulumi_operator.stack.up(local_command_stack)
        initial_outputs = up_result.outputs

        rename_stack = RenameTargetProject.stack(local_command_stack.target)
        rename_result = pulumi_operator.stack.rename(local_command_stack, rename_stack)

        rename_pstack = pulumi_operator.stack.tools.pulumi_stack(rename_stack)
        rename_outputs = rename_pstack.outputs()

        assert rename_result.summary is not None
        assert rename_result.summary.result == "succeeded"
        assert rename_outputs["tempfile"].value == initial_outputs["tempfile"].value

    def test_stack_rename_source_matches_dest(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests renaming a stack when the source and destination are the same.
        """
        with pytest.raises(auto.StackAlreadyExistsError):
            pulumi_operator.stack.rename(local_command_stack, local_command_stack)

    def test_stack_outputs_access(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests accessing the stack outputs of dependencies.

        The depender gets the output from the dependency. The depender re-exports the
        retrieved value. The outputs are checked to ensure they are equal.
        """
        depender_stack = DependerProject.stack(DeploymentTarget(Environment.TEST, None))
        dependency_up_result = pulumi_operator.stack.up(local_command_stack)
        depender_up_result = pulumi_operator.stack.up(depender_stack)

        def ov(result: auto.UpResult) -> str:
            return str(result.outputs["tempfile"].value)

        assert ov(depender_up_result) == ov(dependency_up_result)

    def test_stack_outputs_rejected_for_non_dependency(
        self,
        pulumi_operator: PulumiOperator,
        local_command_stack: InfrastructureStack,
    ) -> None:
        """
        Tests that accessing stack outputs is rejected when the outputs to be
        fetched are from a stack which is not a declared dependency.
        """
        depender_stack = DependerProject.stack(
            DeploymentTarget(Environment.TEST, "us-west-2")
        )

        pulumi_operator.stack.up(local_command_stack)

        # The UndeclaredDependencyError gets eaten by Pulumi. :-(
        with pytest.raises(auto.InlineSourceRuntimeError) as exc_info:
            pulumi_operator.stack.up(depender_stack)

        assert "UndeclaredDependencyError" in str(exc_info.value)


class TestPulumiStackDescription:
    """
    Contains tests for the PulumiStackDescription class.
    """

    @pytest.mark.parametrize(
        "f",
        [
            lambda: PulumiStackDescription(
                stack=LocalCommandProject.stack(
                    DeploymentTarget(Environment.TEST, None)
                ),
                code=True,
                state=False,
            ),
            lambda: PulumiStackDescription(
                stack=LocalCommandProject.stack(
                    DeploymentTarget(Environment.TEST, None)
                ),
                code=False,
                state=True,
            ),
        ],
    )
    def test_eq_equivalent_object(
        self,
        f: Callable[[], PulumiStackDescription],
    ) -> None:
        """
        Tests that PulumiStackDescription compares equal with equivalent objects.
        """
        a = f()
        b = f()

        assert a == b

    @pytest.mark.parametrize(
        "a, b",
        [
            (  # Test case: project differs
                PulumiStackDescription(
                    stack=LocalCommandProject.stack(
                        DeploymentTarget(Environment.TEST, None),
                    ),
                    code=True,
                    state=False,
                ),
                PulumiStackDescription(
                    stack=DependerProject.stack(
                        DeploymentTarget(Environment.TEST, None),
                    ),
                    code=True,
                    state=False,
                ),
            ),
            (  # Test case: code differs
                PulumiStackDescription(
                    stack=LocalCommandProject.stack(
                        DeploymentTarget(Environment.TEST, None),
                    ),
                    code=True,
                    state=False,
                ),
                PulumiStackDescription(
                    stack=LocalCommandProject.stack(
                        DeploymentTarget(Environment.TEST, None),
                    ),
                    code=False,
                    state=False,
                ),
            ),
            (  # Test case: state differs
                PulumiStackDescription(
                    stack=LocalCommandProject.stack(
                        DeploymentTarget(Environment.TEST, None),
                    ),
                    code=True,
                    state=True,
                ),
                PulumiStackDescription(
                    stack=LocalCommandProject.stack(
                        DeploymentTarget(Environment.TEST, None),
                    ),
                    code=True,
                    state=False,
                ),
            ),
        ],
    )
    def test_eq_unequivalent_objects(
        self,
        a: PulumiStackDescription,
        b: PulumiStackDescription,
    ) -> None:
        """
        Tests that PulumiStackDescription compares unequal with unequivalent objects.
        """

    @pytest.mark.parametrize(
        "other",
        [
            0,
            False,
            True,
            None,
            "stack",
        ],
    )
    def test_eq_dissimilar_object(self, other: Any) -> None:
        """
        Tests that PulumiStackDescription compares unequal with dissimilar objects.
        """
        sd = PulumiStackDescription(
            stack=LocalCommandProject.stack(DeploymentTarget(Environment.TEST, None)),
            code=True,
            state=True,
        )

        assert sd != other
