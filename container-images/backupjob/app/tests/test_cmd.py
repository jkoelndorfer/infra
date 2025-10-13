"""
Tests command invocation helpers.
"""

from pathlib import Path

import pytest

from backup.cmd import cmdexec, CommandExecutorProtocol


class TestCmdExec:
    """
    Tests the command executor.
    """

    def test_invoke_successful_cmd(self) -> None:
        """
        Tests invocation of a successful command.
        """
        result = cmdexec(
            ["sh", "-c", "exit 0"], cwd=Path.cwd(), combine_stdout_stderr=True
        )

        assert result.returncode == 0

    def test_invoke_failed_cmd(self) -> None:
        """
        Tests invocation of a failed command.
        """
        result = cmdexec(
            ["sh", "-c", "exit 1"], cwd=Path.cwd(), combine_stdout_stderr=True
        )

        assert result.returncode == 1

    def test_stdout_stderr_combined(self) -> None:
        """
        Tests that the output from stdout and stderr are combined when
        combine_stdout_stderr is truthy.
        """

        result = cmdexec(
            ["sh", "-c", "printf 'stdout data\n'; printf 'stderr data\n' >&2"],
            cwd=Path.cwd(),
            combine_stdout_stderr=True,
        )

        assert result.stdout == b"stdout data\nstderr data\n"

    def test_stdout_stderr_separate(self) -> None:
        """
        Tests that the output from stdout and stderr are not separate when
        combine_stdout_stderr is falsy.
        """

        result = cmdexec(
            ["sh", "-c", "printf 'stdout data\n'; printf 'stderr data\n' >&2"],
            cwd=Path.cwd(),
            combine_stdout_stderr=False,
        )

        assert result.stdout == b"stdout data\n"
        assert result.stderr == b"stderr data\n"
