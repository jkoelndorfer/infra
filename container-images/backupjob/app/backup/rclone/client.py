"""
backup.rclone.client
====================

Contains the implementation for the rclone client.
"""

import json
from pathlib import Path
from typing import Optional, Type, TypeVar

from ..cmd import CommandExecutorProtocol
from .model import RcloneResult, RcloneSyncResult


RR = TypeVar("RR", bound=RcloneResult)


class RcloneClient:
    """
    Client to the rclone binary.

    This client provides only a subset of functionality to perform syncs and checks.
    """

    def __init__(self, cmdexec: CommandExecutorProtocol) -> None:
        self.cmdexec = cmdexec
        self.provider_args: list[str] = list()
        self.sync_args: list[str] = list()

    def full_cmd(self, *cmd: str) -> list[str]:
        """
        Given an rclone subcommand, returns the full rclone command to be invoked.
        """
        return [
            "rclone",
            "--verbose",
            "--use-json-log",
            *cmd,
        ]

    def run(self, *cmd: str, result_type: Type[RR], cwd: Optional[Path]) -> RR:
        """
        Runs rclone with the given command, returning all the messages produced by rclone.
        """
        if cwd is None:
            cwd = Path.cwd()
        full_cmd = self.full_cmd(*cmd)
        proc = self.cmdexec(full_cmd, cwd, combine_stdout_stderr=True)
        messages = list(map(lambda ln: json.loads(ln), proc.stdout.splitlines(b"\n")))

        return result_type(list(cmd), full_cmd, proc.returncode, messages)

    def sync(self, source: str, destination: str) -> RcloneSyncResult:
        """
        Performs a sync using rclone.
        """
        return self.run(
            *self.provider_args,
            "sync",
            *self.sync_args,
            source,
            destination,
            result_type=RcloneSyncResult,
            cwd=None,
        )
