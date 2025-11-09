"""
backup.cmd
==========

Contains code to invoke commands.
"""

from pathlib import Path
import subprocess
from typing import Protocol

from .log import logger

log = logger("cmd")


class CommandExecutorProtocol(Protocol):
    """
    Protocol describing a command executor.
    """

    def __call__(
        self, cmd: list[str], cwd: Path, combine_stdout_stderr: bool
    ) -> subprocess.CompletedProcess:
        """
        Invokes the given command and returns the resulting CompletedProcess.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not provide an implementation"
        )  # pragma: nocover


def cmdexec(
    cmd: list[str], cwd: Path, combine_stdout_stderr: bool
) -> subprocess.CompletedProcess:
    """
    Command runner that maintains separate stdout and stderr streams.
    """
    if combine_stdout_stderr:
        stderr = subprocess.STDOUT
    else:
        stderr = subprocess.PIPE

    log.info(f"executing command {cmd} in {cwd}")
    proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=stderr)
    log.info(proc.stdout)
    if not combine_stdout_stderr:
        log.info(proc.stderr)
    return proc


# Ensure cmdexec satisfies the CommandExecutorProtocol.
_: CommandExecutorProtocol = cmdexec
