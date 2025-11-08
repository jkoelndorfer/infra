"""
backup.restic.model
===================

Contains models for restic data.
"""

from datetime import datetime
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
        self._summary_dict: Optional[dict] = self.find_summary_dict(messages)

    @classmethod
    def find_summary_dict(cls, messages: list[dict]) -> Optional[dict]:
        """
        Searches the given messages to find the "summary" message.
        """
        for m in messages:
            # Single JSON document commands don't really have "messages", so this field
            # is not guaranteed to exist.
            if m.get("message_type", None) == "summary":
                return m
        return None


class ResticBackupSummary:
    """
    Object representing the "summary" field displayed as the result of a Restic backup
    or when listing Restic snapshots.
    """

    def __init__(
        self,
        snapshot_id: Optional[str],
        backup_start: datetime,
        backup_end: datetime,
        files_new: int,
        files_changed: int,
        files_unmodified: int,
        dirs_new: int,
        dirs_changed: int,
        data_blobs: int,
        tree_blobs: int,
        data_added: int,
        data_added_packed: int,
        total_files_processed: int,
        total_bytes_processed: int,
    ) -> None:
        self.snapshot_id = snapshot_id
        self.backup_start = backup_start
        self.backup_end = backup_end
        self.files_new = files_new
        self.files_changed = files_changed
        self.files_unmodified = files_unmodified
        self.dirs_new = dirs_new
        self.dirs_changed = dirs_changed
        self.data_blobs = data_blobs
        self.tree_blobs = tree_blobs
        self.data_added = data_added
        self.data_added_packed = data_added_packed
        self.total_files_processed = total_files_processed
        self.total_bytes_processed = total_bytes_processed


class ResticBackupResult(ResticResult):
    """
    Object representing the result of a `restic backup` invocation.

    `restic backup` returns several message types.

        Status:         https://restic.readthedocs.io/en/stable/075_scripting.html#status
        Error:          https://restic.readthedocs.io/en/stable/075_scripting.html#error
        Verbose Status: https://restic.readthedocs.io/en/stable/075_scripting.html#verbose-status
        Summary:        https://restic.readthedocs.io/en/stable/075_scripting.html#summary
    """

    def __init__(
        self,
        repository: str,
        cmd: list[str],
        full_cmd: list[str],
        returncode: int,
        messages: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            repository=repository,
            cmd=cmd,
            full_cmd=full_cmd,
            returncode=returncode,
            messages=messages,
        )

        self.summary: Optional[ResticBackupSummary] = None

        if self.returncode == ResticReturnCode.RC_OK:
            assert self._summary_dict is not None

            self.summary = ResticBackupSummary(
                snapshot_id=self._summary_dict.get("snapshot_id", None),
                backup_start=datetime.fromisoformat(self._summary_dict["backup_start"]),
                backup_end=datetime.fromisoformat(self._summary_dict["backup_end"]),
                files_new=self._summary_dict["files_new"],
                files_changed=self._summary_dict["files_changed"],
                files_unmodified=self._summary_dict["files_unmodified"],
                dirs_new=self._summary_dict["dirs_new"],
                dirs_changed=self._summary_dict["dirs_changed"],
                data_blobs=self._summary_dict["data_blobs"],
                tree_blobs=self._summary_dict["tree_blobs"],
                data_added=self._summary_dict["data_added"],
                data_added_packed=self._summary_dict["data_added_packed"],
                total_files_processed=self._summary_dict["total_files_processed"],
                total_bytes_processed=self._summary_dict["total_bytes_processed"],
            )


class ResticCheckSummary:
    """
    Object representing the summary of a `restic check` invocation.
    """

    def __init__(
        self,
        num_errors: int,
        broken_packs: Optional[list[str]],
        suggest_repair_index: bool,
        suggest_prune: bool,
    ) -> None:
        self.num_errors = num_errors
        self.broken_packs = broken_packs
        self.suggest_repair_index = suggest_repair_index
        self.suggest_prune = suggest_prune


class ResticCheckResult(ResticResult):
    """
    Object representing the result of a `restic check` invocation.

    `restic check` returns two message types:

    Summary: https://restic.readthedocs.io/en/stable/075_scripting.html#id2
    Error:   https://restic.readthedocs.io/en/stable/075_scripting.html#id3

    Summary messages are as below, assuming no errors were found:

        {"message_type":"summary","num_errors":0,"broken_packs":null,"suggest_repair_index":false,"suggest_prune":false}
    """

    def __init__(
        self,
        repository: str,
        cmd: list[str],
        full_cmd: list[str],
        returncode: int,
        messages: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            repository=repository,
            cmd=cmd,
            full_cmd=full_cmd,
            returncode=returncode,
            messages=messages,
        )

        self.summary: Optional[ResticCheckSummary] = None

        if self.returncode == ResticReturnCode.RC_OK:
            assert self._summary_dict is not None

            self.summary = ResticCheckSummary(
                num_errors=self._summary_dict["num_errors"],
                broken_packs=self._summary_dict["broken_packs"],
                suggest_repair_index=self._summary_dict["suggest_repair_index"],
                suggest_prune=self._summary_dict["suggest_prune"],
            )
