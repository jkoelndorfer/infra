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
        summary = result.summary or dict()

        report.new_field(
            "Errors",
            summary.get("num_errors", None),
            lambda x: A.OK if x == 0 else A.ERROR,
        )
        report.new_field(
            "Repair Suggested",
            summary.get("suggest_repair_index", None),
            lambda x: A.OK if x is False else A.ERROR,
        )
        report.new_field(
            "Prune Suggested",
            summary.get("suggest_prune", None),
            lambda x: A.OK if x is False else A.ERROR,
        )

        if summary.get("num_errors", 1) == 0:
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

        summary = dict()
        if result.summary is not None:
            summary = result.summary

        snapshot_id = summary.get("snapshot_id", None)

        if result.returncode != ResticReturnCode.RC_OK:
            report.new_field(
                "Error",
                summary.get("message", None) or "(no message)",
                lambda x: A.MULTILINE_TEXT,
            )
            return

        report.new_field(
            "New Files",
            summary.get("files_new", None),
            lambda x: A.ERROR if x is None else None,
        )
        report.new_field(
            "Files Changed",
            summary.get("files_changed", None),
            lambda x: A.ERROR if x is None else None,
        )
        report.new_field(
            "Data Added",
            summary.get("data_added", None),
            lambda x: A.ERROR if x is None else None,
        )
        report.new_field(
            "Total Bytes Processed",
            summary.get("total_bytes_processed", None),
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
