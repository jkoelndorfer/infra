"""
backup.restic.service
=====================

Contains the implementation for the restic service.
"""

from datetime import datetime
from pathlib import Path

from ..report import (
    BackupReport,
    BackupReportField as F,
    BackupReportFieldAnnotation as A,
)
from .client import ResticClient
from .model import ResticReturnCode


class ResticService:
    """
    Service providing high-level functionality over a restic repository.
    """

    def __init__(self, client: ResticClient) -> None:
        self.client = client

    def backup(
        self,
        name: str,
        source: Path,
        for_each: bool,
        skip_if_unchanged: bool,
    ) -> BackupReport:
        """
        Performs a backup of the source directory, performing any required
        repository initialization first.

        If for_each is True, runs one backup for each directory and regular
        file that is a child of the source directory.
        """
        report = BackupReport(name=name)
        report.new_field("Repository", self.client.repository_path, lambda x: None)
        new_backup_repo = report.new_field(
            "New Repo", False, lambda x: A.OK if not x else A.WARNING
        )
        init_ok = report.new_field("Init OK", False, lambda x: A.OK if x else A.ERROR)
        report.new_field("Backup Start", datetime.now(), lambda x: None)
        backup_end = report.new_field("Backup End", datetime.now(), lambda x: None)

        try:
            if not self._init_repo(new_backup_repo, init_ok):
                return report

            if for_each:
                self._backup_for_each(source, skip_if_unchanged, report)
            else:
                self._backup_single(source, skip_if_unchanged, report)

            return report
        finally:
            backup_end.data = datetime.now()

    def check(self) -> BackupReport:
        """
        Performs a restic repository check.
        """
        report = BackupReport("Repository Check")
        report.new_field("Repository", self.client.repository_path, lambda x: None)

        result = self.client.check(read_data=True)

        if result.returncode != ResticReturnCode.RC_OK:
            report.new_field(
                "Error Code",
                result.returncode,
                lambda x: A.OK if x == ResticReturnCode.RC_OK else A.ERROR,
            )
            return report

        summary = result.summary
        assert summary is not None

        report.new_field(
            "Errors",
            summary.num_errors,
            lambda x: A.OK if x == 0 else A.ERROR,
        )
        report.new_field(
            "Repair Suggested",
            summary.suggest_repair_index,
            lambda x: A.OK if x is False else A.ERROR,
        )
        report.new_field(
            "Prune Suggested",
            summary.suggest_prune,
            lambda x: A.OK if x is False else A.ERROR,
        )

        if summary.num_errors == 0:
            report.successful = True

        return report

    def compare_latest_snapshots(self, remote_client: ResticClient) -> BackupReport:
        """
        Compares the most recent snapshot between the local repository
        (accessed this service object's ResticClient) and a remote
        repository (accessed via the remote_client).

        The report is successful if the local and remote repositories' latest
        snapshots are the same.
        """
        report = BackupReport("Snapshot Comparison")
        report.new_field(
            "Local Repository", self.client.repository_path, lambda x: None
        )
        report.new_field(
            "Remote Repository", remote_client.repository_path, lambda x: None
        )
        local_snap_result = self.client.snapshots(latest=1)
        remote_snap_result = remote_client.snapshots(latest=1)
        no_snapshot = "(none)"

        local_snap_id = no_snapshot
        if len(local_snap_result.snapshots) > 0:
            local_snap_id = local_snap_result.snapshots[-1].id

        remote_snap_id = no_snapshot
        if len(remote_snap_result.snapshots) > 0:
            remote_snap_id = remote_snap_result.snapshots[-1].id

        report.new_field(
            "Local Snapshot ID",
            local_snap_id,
            lambda x: A.ERROR if local_snap_id == no_snapshot else None,
        )
        report.new_field(
            "Remote Snapshot ID",
            remote_snap_id,
            lambda x: A.ERROR if local_snap_id == no_snapshot else None,
        )

        if local_snap_id == remote_snap_id and local_snap_id != no_snapshot:
            report.successful = True

        return report

    def _backup_for_each(
        self,
        source: Path,
        skip_if_unchanged: bool,
        report: BackupReport,
    ) -> None:
        """
        Performs one restic backup for each directory inside source.

        A subreport is produced for each backed-up directory if there were changes.
        """
        all_subreports: list[BackupReport] = list()

        for p in source.iterdir():
            if p.is_file() or p.is_dir():
                subreport = BackupReport(f"{report.name} / {p.name}")
                all_subreports.append(subreport)
                subreport.new_field("Backup Start", datetime.now(), lambda x: None)
                backup_end = subreport.new_field(
                    "Backup End", datetime.now(), lambda x: None
                )
                try:
                    self._backup_single(p, skip_if_unchanged, subreport)
                    report.add_subreport(subreport)
                finally:
                    backup_end.data = datetime.now()

        report.successful = all(r.successful for r in all_subreports)

    def _backup_single(
        self,
        source: Path,
        skip_if_unchanged: bool,
        report: BackupReport,
    ) -> None:
        """
        Performs a single directory backup.
        """
        report.new_field("Directory", str(source), lambda x: None)

        try:
            result = self.client.backup(source, skip_if_unchanged)
        except Exception as e:  # pragma: nocover
            report.new_field("Error", str(e), lambda x: A.MULTILINE_TEXT)
            return

        summary = result.summary

        if result.returncode != ResticReturnCode.RC_OK:
            report.new_field(
                "Error",
                "backup failed",
                lambda x: None,
            )
            return

        assert summary is not None
        snapshot_id = summary.snapshot_id

        report.new_field(
            "New Files",
            summary.files_new,
            lambda x: A.ERROR if x is None else None,
        )
        report.new_field(
            "Files Changed",
            summary.files_changed,
            lambda x: A.ERROR if x is None else None,
        )
        report.new_field(
            "Data Added",
            summary.data_added,
            lambda x: A.ERROR if x is None else None,
        )
        report.new_field(
            "Total Bytes Processed",
            summary.total_bytes_processed,
            lambda x: A.ERROR if x is None else None,
        )
        report.new_field(
            "Snapshot ID",
            snapshot_id,
            lambda x: A.ERROR if x is None else None,
        )

        if skip_if_unchanged and snapshot_id is None:
            report.omittable = True

        report.successful = True

    def _init_repo(self, new_backup_repo: F[bool], init_ok: F[bool]) -> bool:
        """
        Ensures the backup repository is initialized. Adds fields to the report
        to indicate the repository status.

        Returns True if initialization succeeds, False otherwise.
        """
        init_ok.data = False

        if not self.client.repository_is_initialized():
            new_backup_repo.data = True

            try:
                init_result = self.client.init()
            except Exception:
                return False

            if init_result.returncode != ResticReturnCode.RC_OK:  # pragma: nocover
                # The client should always raise an exception if init fails.
                # Just in case, we double-check here.
                return False

        init_ok.data = True

        return True
