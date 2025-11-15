"""
backup.restic.model
===================

Contains models for restic data.
"""

from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, Optional, Self


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
        dirs_unmodified: int,
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
        self.dirs_unmodified = dirs_unmodified
        self.data_blobs = data_blobs
        self.tree_blobs = tree_blobs
        self.data_added = data_added
        self.data_added_packed = data_added_packed
        self.total_files_processed = total_files_processed
        self.total_bytes_processed = total_bytes_processed

    @classmethod
    def from_dict(cls, snapshot_id: Optional[str], d: dict) -> Self:
        """
        Given a dictionary with backup summary fields as returned by restic,
        returns a corresponding ResticBackupSummary object.
        """
        return cls(
            snapshot_id=snapshot_id,
            backup_start=datetime.fromisoformat(d["backup_start"]),
            backup_end=datetime.fromisoformat(d["backup_end"]),
            files_new=d["files_new"],
            files_changed=d["files_changed"],
            files_unmodified=d["files_unmodified"],
            dirs_new=d["dirs_new"],
            dirs_changed=d["dirs_changed"],
            dirs_unmodified=d["dirs_unmodified"],
            data_blobs=d["data_blobs"],
            tree_blobs=d["tree_blobs"],
            data_added=d["data_added"],
            data_added_packed=d["data_added_packed"],
            total_files_processed=d["total_files_processed"],
            total_bytes_processed=d["total_bytes_processed"],
        )


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

            self.summary = ResticBackupSummary.from_dict(
                snapshot_id=self._summary_dict.get("snapshot_id", None),
                d=self._summary_dict,
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


class ResticSnapshot:
    """
    Object representing an individual restic snapshot.
    """

    def __init__(
        self,
        time: datetime,
        parent: Optional[str],
        tree: str,
        paths: list[Path],
        hostname: str,
        username: str,
        program_version: str,
        id: str,
        short_id: str,
        summary: ResticBackupSummary,
    ) -> None:
        self.time = time
        self.parent = parent
        self.tree = tree
        self.paths = paths
        self.hostname = hostname
        self.username = username
        self.program_version = program_version
        self.id = id
        self.short_id = short_id
        self.summary = summary

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """
        Given a dictionary with fields representing a restic snapshot, returns
        a ResticSnapshot.
        """
        return cls(
            time=datetime.fromisoformat(d["time"]),
            parent=d.get("parent", None),
            tree=d["tree"],
            paths=[Path(p) for p in d["paths"]],
            hostname=d["hostname"],
            username=d["username"],
            program_version=d["program_version"],
            id=d["id"],
            short_id=d["short_id"],
            summary=ResticBackupSummary.from_dict(snapshot_id=d["id"], d=d["summary"]),
        )


class ResticSnapshotsResult(ResticResult):
    """
    Object representing the result of a `restic snapshots` invocation.
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

        self.snapshots: list[ResticSnapshot] = list()

        if self.returncode == ResticReturnCode.RC_OK:
            for sd in self.messages:
                self.snapshots.append(ResticSnapshot.from_dict(sd))
