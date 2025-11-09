"""
backup.rclone.model
===================

Contains the implementation for rclone models.
"""

from typing import Any


class RcloneResult:
    """
    Object representing the result of an rclone invocation.
    """

    def __init__(
        self,
        cmd: list[str],
        full_cmd: list[str],
        returncode: int,
        messages: list[dict[str, Any]],
    ) -> None:
        # The rclone command that was run. Does not include the path to the rclone binary
        # or implied arguments.
        self.cmd = cmd

        # The full rclone command that was executed.
        self.full_cmd = full_cmd

        # The return code of the rclone binary.
        self.returncode = returncode

        # The list of all JSON-encoded messages emitted by rclone when the command was run.
        self.messages = messages


class RcloneSyncStatistics:
    """
    Object representing rclone sync statistics.

    See https://rclone.org/rc/#core-stats.
    """

    def __init__(self, raw: dict) -> None:
        self.raw = raw

    @property
    def bytes(self) -> int:
        """
        Bytes transferred during the sync.
        """
        return self.raw["bytes"]

    @property
    def deletes(self) -> int:
        """
        Numbers of files deleted.
        """
        return self.raw["deletes"]

    @property
    def errors(self) -> int:
        """
        Number of errors that occurred during the sync.
        """
        return self.raw["errors"]

    @property
    def transfers(self) -> int:
        """
        Number of files transferred.
        """
        return self.raw["transfers"]


class RcloneSyncResult(RcloneResult):
    """
    Object representing an `rclone sync` result.
    """

    def __init__(
        self,
        cmd: list[str],
        full_cmd: list[str],
        returncode: int,
        messages: list[dict[str, Any]],
    ) -> None:
        super().__init__(cmd, full_cmd, returncode, messages)

        self.stats = RcloneSyncStatistics(messages[-1]["stats"])
