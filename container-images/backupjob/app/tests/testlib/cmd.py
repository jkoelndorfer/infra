"""
testlib.cmd
===========

Contains code to mock command execution.
"""

import json
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Callable, Optional, Tuple

from backup.cmd import CommandExecutorProtocol

CommandResultFactoryOutput = Tuple[int, bytes, Optional[bytes]]
CommandResultFactory = Callable[[list[str], Path, bool], CommandResultFactoryOutput]


def _default_result_factory(
    cmd: list[str], cwd: Path, combine_stdout_stderr: bool
) -> Tuple[int, bytes, bytes]:
    raise NotImplementedError(
        "MockCommandExecutor does not provide a default command result"
    )


class MockCommandExecutor:
    """
    Class that mocks command execution.
    """

    def __init__(self) -> None:
        self.invoked_commands: list[MockInvokedCommand] = list()
        self.cmd_result_factory: CommandResultFactory = _default_result_factory

    def set_result(
        self, returncode: int, stdout: bytes, stderr: Optional[bytes]
    ) -> None:
        """
        Sets the result for this MockCommandExecutor. The returncode, stdout, and stderr
        values are returned irrespective of any command that is supplied.
        """

        def static_result_factory(
            cmd: list[str], cwd: Path, combine_stdout_stderr: bool
        ) -> CommandResultFactoryOutput:
            return (returncode, stdout, stderr)

        self.cmd_result_factory = static_result_factory

    def set_result_json_messages(self, returncode: int, messages: list[dict]) -> None:
        """
        Sets a restic result for this MockCommandExecutor.

        A restic result contains zero or more line-delimited JSON objects on stdout.
        """
        stdout = "\n".join(json.dumps(m) for m in messages)
        self.set_result(returncode, stdout.encode("utf-8"), None)

    def __call__(
        self, cmd: list[str], cwd: Path, combine_stdout_stderr: bool
    ) -> CompletedProcess:
        """
        Accepts a command and returns a result in accordance with this object's configuration.
        """
        returncode, stdout, stderr = self.cmd_result_factory(
            cmd, cwd, combine_stdout_stderr
        )
        self.invoked_commands.append(MockInvokedCommand(cmd, cwd))
        return CompletedProcess(cmd, returncode, stdout, stderr)


class MockInvokedCommand:
    """
    Class representing a mock command invocation.
    """

    def __init__(self, cmd: list[str], cwd: Path) -> None:
        self.cmd = cmd
        self.cwd = cwd

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            # If the compared object is another MockInvokedCommand, compare
            # the current working directory too, because we might care about that.
            return self.cmd == other.cmd and self.cwd == other.cwd
        elif isinstance(other, list):
            # If the compared object is a list, it should be a list of strings (or:
            # a command). In that case, just check that our command matches.
            return self.cmd == other
        else:
            # Everything else is non-comparable.
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(cwd={str(self.cwd)}, cmd={self.cmd})"


_: CommandExecutorProtocol = MockCommandExecutor()
