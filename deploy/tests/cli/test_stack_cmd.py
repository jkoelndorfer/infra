"""
tests/cli/test_stack_cmd -- CLI stack Command Tests
===================================================

This file contains code to test the stack subcommand of the CLI.
"""

from click import Group
from click.testing import CliRunner

from infralib import (
    InfrastructureProject,
    InfrastructureStack,
    DeploymentTarget,
    Environment,
)


class CLITestProject(InfrastructureProject):
    """
    InfrastructureProject used for CLI tests.

    This project does nothing.
    """

    name = "test.cli.integration"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.TEST, None),
            DeploymentTarget(Environment.DEV, None),
        ]

    def pulumi_program(self) -> None:
        pass


class CLITestRenamedProject(InfrastructureProject):
    """
    InfrastructureProject used as a rename target for CLI testing.

    This project does nothing.
    """

    name = "test.cli.rename"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(Environment.TEST, None)]

    def pulumi_program(self) -> None:
        pass


def stack_cmd(*cmd: str) -> list[str]:
    """
    Creates a stack command for the test.cli.integration project.
    """
    return ["stack", *cmd, "-e", "test", "-p", CLITestProject.name]


class TestCLIStackSubcommand:
    """
    This class tests the CLI's stack subcommand.
    """

    # Text printed when a destroy operation is aborted.
    #
    # This text originates from this project.
    DESTROY_ABORTED = "stack destroy aborted"

    # Text printed when the CLI is previewing a destroy operation.
    #
    # This text originates from the Pulumi CLI.
    DESTROY_PREVIEW = "Previewing destroy"

    # Text printed when the CLI is confirming whether a destroy should proceed.
    #
    # This text originates from this project.
    DESTROY_CONFIRMATION = "proceed with destroying stack"

    # Text printed when the CLI is finished destroying a stack.
    #
    # This text originates from the Pulumi CLI.
    DESTROY_COMPLETE = "The resources in the stack have been deleted"

    # Text printed when an up operation is aborted.
    #
    # This text originates from this project.
    UP_ABORTED = "stack up aborted"

    # Text printed when the CLI is previewing an up operation.
    #
    # This text originates from the Pulumi CLI.
    UP_PREVIEW = "Previewing update"

    # Text printed when the CLI is confirming whether an up operation should proceed.
    #
    # This text originates from this project.
    UP_CONFIRMATION = "proceed with upping stack"

    # Text printed when the CLI is finished upping a stack.
    #
    # This text originates from the Pulumi CLI.
    UP_COMPLETE = "Duration:"

    def test_list(self, cli_main: Group, cli_runner: CliRunner) -> None:
        """
        Tests listing stacks.
        """
        stack_list = cli_runner.invoke(cli_main, ["stack", "list"])

        assert stack_list.exit_code == 0

    def test_up_destroy(self, cli_main: Group, cli_runner: CliRunner) -> None:
        """
        Tests upping a stack, then destroying it.
        """
        stack_up = cli_runner.invoke(cli_main, stack_cmd("up"), input="y\n")
        stack_destroy = cli_runner.invoke(cli_main, stack_cmd("destroy"), input="y\n")

        assert stack_up.exit_code == 0
        assert self.UP_PREVIEW in stack_up.stdout
        assert self.UP_CONFIRMATION in stack_up.stdout
        assert self.UP_COMPLETE in stack_up.stdout

        assert stack_destroy.exit_code == 0
        assert self.DESTROY_PREVIEW in stack_destroy.stdout
        assert self.DESTROY_CONFIRMATION in stack_destroy.stdout
        assert self.DESTROY_COMPLETE in stack_destroy.stdout

    def test_up_destroy_no_confirm(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        """
        Tests upping a stack, then destroying it without confirmation.
        """
        stack_up = cli_runner.invoke(cli_main, stack_cmd("up", "--no-confirm"))
        stack_destroy = cli_runner.invoke(
            cli_main, stack_cmd("destroy", "--no-confirm")
        )

        assert stack_up.exit_code == 0
        assert self.UP_CONFIRMATION not in stack_up.stdout
        assert self.UP_COMPLETE in stack_up.stdout

        assert stack_destroy.exit_code == 0
        assert self.DESTROY_CONFIRMATION not in stack_up.stdout
        assert self.DESTROY_COMPLETE in stack_destroy.stdout

    def test_up_abort(self, cli_main: Group, cli_runner: CliRunner) -> None:
        """
        Tests upping a stack and aborting during confirmation.
        """
        stack_up = cli_runner.invoke(cli_main, stack_cmd("up"), input="n\n")

        assert self.UP_ABORTED in stack_up.stdout
        assert stack_up.return_value is None

    def test_destroy_abort(self, cli_main: Group, cli_runner: CliRunner) -> None:
        """
        Tests destroying a stack and aborting during confirmation.
        """
        stack_destroy = cli_runner.invoke(cli_main, stack_cmd("destroy"), input="n\n")

        assert self.DESTROY_ABORTED in stack_destroy.stdout
        assert stack_destroy.return_value is None

    def test_preview(self, cli_main: Group, cli_runner: CliRunner) -> None:
        """
        Tests previewing a stack.
        """
        stack_preview = cli_runner.invoke(cli_main, stack_cmd("preview"))

        assert stack_preview.exit_code == 0
        assert self.UP_PREVIEW in stack_preview.stdout

    def test_preview_destroy(self, cli_main: Group, cli_runner: CliRunner) -> None:
        """
        Tests previewing a stack destroy.
        """
        stack_preview = cli_runner.invoke(cli_main, stack_cmd("preview", "--destroy"))

        assert stack_preview.exit_code == 0
        assert self.DESTROY_PREVIEW in stack_preview.stdout

    def test_up_invalid_project(self, cli_main: Group, cli_runner: CliRunner) -> None:
        """
        Tests upping a stack for a project that does not exist.
        """
        stack_up = cli_runner.invoke(
            cli_main, ["stack", "up", "-e", "test", "-p", "test.cli.doesnotexist"]
        )

        assert stack_up.exit_code != 0
        assert "no such project:" in stack_up.stderr

    def test_up_invalid_deployment_target(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        """
        Tests upping a stack when the deployment target is not valid.
        """
        stack_up = cli_runner.invoke(cli_main, stack_cmd("up", "-r", "invalid-region"))

        assert stack_up.exit_code != 0
        assert "invalid deployment target for project" in stack_up.stderr

    def test_up_rename_new_project(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        """
        Tests upping a stack, then renaming it under a new project.
        """
        cli_runner.invoke(cli_main, stack_cmd("up"))
        rename = cli_runner.invoke(
            cli_main, stack_cmd("rename", "--to-project", CLITestRenamedProject.name)
        )

        assert rename.exit_code == 0

    def test_up_rename_new_environment(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        """
        Tests upping a stack, then renaming it under a new environment
        """
        cli_runner.invoke(cli_main, stack_cmd("up"))
        rename = cli_runner.invoke(
            cli_main, stack_cmd("rename", "--to-environment", Environment.DEV)
        )

        assert rename.exit_code == 0

    def test_up_rename_source_matches_dest(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        """
        Tests upping a stack, then attempting to rename the stack to its current name.

        Pulumi does not permit this; it will raise a StackAlreadyExistsError.
        """
        cli_runner.invoke(cli_main, stack_cmd("up"))
        rename = cli_runner.invoke(
            cli_main, stack_cmd("rename", "--to-project", CLITestProject.name)
        )

        assert rename.exit_code == 1
