"""
backup.rclone.service
=====================

Contains the implementation for the rclone service.
"""

from datetime import datetime

from ..report import BackupReport, BackupReportFieldAnnotation as A
from .client import RcloneClient
from .model import RcloneResult


class RcloneService:
    """
    Service providing high-level functionality over rclone.
    """

    def __init__(self, client: RcloneClient) -> None:
        self.client = client

    def sync(
        self, name: str, source: str, destination: str
    ) -> BackupReport[RcloneResult]:
        """
        Performs an rclone sync from the source to the destination,
        producing a backup report.
        """
        report = BackupReport(name=f"rclone sync / {name}")
        report.new_field("Source", source, lambda _: None)
        report.new_field("Destination", destination, lambda _: None)
        report.new_field("Backup Start", datetime.now(), lambda _: None)
        backup_end = report.new_field("Backup End", datetime.now(), lambda _: None)

        result = self.client.sync(source, destination)
        report.result = result

        report.successful = result.stats.errors == 0
        report.new_field(
            "Errors", result.stats.errors, lambda x: A.OK if x == 0 else A.ERROR
        )
        report.new_field("Bytes Transferred", result.stats.bytes, lambda _: None)
        report.new_field("Files Transferred", result.stats.transfers, lambda _: None)
        report.new_field("Deletes", result.stats.deletes, lambda _: None)

        backup_end.data = datetime.now()
        return report
