"""
backup.restic.service
=====================

Contains the implementation for the restic service.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from ..report import (
    BackupReport,
    BackupReportField as F,
    BackupReportFieldAnnotation as A,
)
from .client import ResticClient
from .error import ResticError
from .model import ResticCheckResult, ResticResult, ResticReturnCode


class ResticService:
    """
    Service providing high-level functionality over a restic repository.
    """

    def __init__(self, client: ResticClient) -> None:
        self.client = client
        self.implicit_exclude_file_name = "backupignore"

    def backup(
        self,
        name: str,
        source: Path,
        for_each: bool,
        skip_if_unchanged: bool,
        exclude_files: list[Path],
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

        exclude_files = exclude_files.copy()

        try:
            inited, result = self._init_repo(new_backup_repo, init_ok)
            if not inited:
                report.result = result
                return report

            if for_each:
                self._backup_for_each(
                    source, skip_if_unchanged, exclude_files.copy(), report
                )
            else:
                self._backup_single(
                    source, skip_if_unchanged, exclude_files.copy(), report
                )

            return report
        finally:
            backup_end.data = datetime.now()

    def check(self) -> BackupReport[ResticCheckResult]:
        """
        Performs a restic repository check.
        """
        report = BackupReport("Repository Check")
        report.new_field("Repository", self.client.repository_path, lambda x: None)
        report.new_field("Check Start", datetime.now(), lambda x: None)
        check_end = report.new_field("Check End", datetime.now(), lambda x: None)

        result = self.client.check(read_data=True)
        report.result = result

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

        check_end.data = datetime.now()

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

        report.result = (local_snap_result, remote_snap_result)

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
        exclude_files: list[Path],
        report: BackupReport,
    ) -> None:
        """
        Performs one restic backup for each directory inside source.

        A subreport is produced for each backed-up directory if there were changes.
        """
        all_subreports: list[BackupReport] = list()
        self._add_implicit_exclude_file(source, exclude_files)

        try:
            for p in source.iterdir():
                if p.is_file() or p.is_dir():
                    subreport = BackupReport(f"{report.name} / {p.name}")
                    all_subreports.append(subreport)
                    subreport.new_field("Backup Start", datetime.now(), lambda x: None)
                    backup_end = subreport.new_field(
                        "Backup End", datetime.now(), lambda x: None
                    )
                    try:
                        self._backup_single(
                            p, skip_if_unchanged, exclude_files.copy(), subreport
                        )
                        report.add_subreport(subreport)
                    finally:
                        backup_end.data = datetime.now()
        except Exception as e:
            report.new_field("Error", str(e), lambda _: None)

        report.successful = (
            all(r.successful for r in all_subreports) and len(all_subreports) > 0
        )

    def _backup_single(
        self,
        source: Path,
        skip_if_unchanged: bool,
        exclude_files: list[Path],
        report: BackupReport,
    ) -> None:
        """
        Performs a single directory backup.
        """
        report.new_field("Directory", str(source), lambda x: None)
        self._add_implicit_exclude_file(source, exclude_files)

        try:
            result = self.client.backup(
                source, skip_if_unchanged, exclude_files=exclude_files
            )
        except Exception as e:  # pragma: nocover
            report.new_field("Error", str(e), lambda x: A.MULTILINE_TEXT)
            return

        report.result = result

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

    def _add_implicit_exclude_file(
        self, source: Path, exclude_files: list[Path]
    ) -> None:
        """
        Adds the implicit backup exclude file to the list of exclude files.

        The implicit backup exclude file is at the root of the backup directory
        with the name "backupignore".
        """
        exclude_file_path = source / self.implicit_exclude_file_name

        try:
            if exclude_file_path.is_file():
                exclude_files.append(exclude_file_path)
        except Exception:
            # If we cannot determine whether the implicit exclude file is a file,
            # we probably can't read the backup source.
            #
            # We'll eat this error so that the backup tries to proceed.
            #
            # In the worst case, restic will fail and produce a result that can
            # be returned later.
            pass

    def _init_repo(
        self, new_backup_repo: F[bool], init_ok: F[bool]
    ) -> Tuple[bool, Optional[ResticResult]]:
        """
        Ensures the backup repository is initialized. Adds fields to the report
        to indicate the repository status.

        Returns True if initialization succeeds, False otherwise.
        """
        init_ok.data = False
        init_result: Optional[ResticResult] = None

        if not self.client.repository_is_initialized():
            new_backup_repo.data = True

            try:
                init_result = self.client.init()
            except ResticError as e:
                return False, e.result

            if init_result.returncode != ResticReturnCode.RC_OK:  # pragma: nocover
                # The client should always raise an exception if init fails.
                # Just in case, we double-check here.
                return False, init_result

        init_ok.data = True

        return True, init_result
