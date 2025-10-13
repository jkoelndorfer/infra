"""
backup.restic.model
===================

Contains models for restic data.
"""

from enum import IntEnum
from typing import Any, Optional


class ResticReturnCode(IntEnum):
    """
    Enum defining exit codes used by Restic.
    """

    # Via the `cat config` command; see
    # https://restic.readthedocs.io/en/stable/075_scripting.html#exit-codes.
    RC_OK = RC_REPOSITORY_INITIALIZED = 0
    RC_REPOSITORY_NOT_INITIALIZED = 10
    RC_BAD_REPOSITORY_PASSWORD = 12


class ResticResult:
    """
    Object representing the result of a restic invocation.
    """

    def __init__(
        self,
        repository: str,
        cmd: list[str],
        full_cmd: list[str],
        returncode: int,
        messages: list[dict[str, Any]],
    ) -> None:
        # The restic repository that produced the result.
        self.repository = repository

        # The restic command that was run. Does not include the path to the restic binary
        # or implied arguments.
        self.cmd = cmd

        # The full restic command that was executed.
        self.full_cmd = full_cmd

        # The return code of the restic binary.
        self.returncode = returncode

        # The list of all JSON-encoded messages emitted by restic when the command was run.
        self.messages = messages

        # The "summary" message. A summary message is not returned by every command. When it
        # is, it contains very useful information.
        self.summary: Optional[dict] = None

        for m in self.messages:
            # Single JSON document commands don't really have "messages", so this field
            # is not guaranteed to exist.
            if m.get("message_type", None) == "summary":
                self.summary = m
                break

    def summary_field(self, field: str) -> Any:
        """
        Returns the given field from the summary message.
        """
        assert self.summary is not None

        return self.summary[field]


class ResticBackupResult(ResticResult):
    """
    Object representing the result of a `restic backup` invocation.

    `restic backup` returns several message types.

        Status:         https://restic.readthedocs.io/en/stable/075_scripting.html#status
        Error:          https://restic.readthedocs.io/en/stable/075_scripting.html#error
        Verbose Status: https://restic.readthedocs.io/en/stable/075_scripting.html#verbose-status
        Summary:        https://restic.readthedocs.io/en/stable/075_scripting.html#summary
    """

    @property
    def snapshot_id(self) -> Optional[str]:
        """
        Returns the snapshot ID of the backup, or None if no snapshot was created.
        """
        return self.summary_field("snapshot_id")


class ResticCheckResult(ResticResult):
    """
    Object representing the result of a `restic check` invocation.

    `restic check` returns two message types:

    Summary: https://restic.readthedocs.io/en/stable/075_scripting.html#id2
    Error:   https://restic.readthedocs.io/en/stable/075_scripting.html#id3

    Summary messages are as below, assuming no errors were found:

        {"message_type":"summary","num_errors":0,"broken_packs":null,"suggest_repair_index":false,"suggest_prune":false}
    """

    @property
    def num_errors(self) -> int:
        """
        Returns the number of errors found during the check.
        """
        return self.summary_field("num_errors")
