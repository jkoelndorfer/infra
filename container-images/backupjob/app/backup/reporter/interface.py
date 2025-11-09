"""
backup.reporter.interface
=========================

Contains the definition for a BackupReporter.
"""

from typing import Any, Protocol

from ..report import BackupReport


class BackupReporter(Protocol):
    """
    Protocol defining the standard interface for backup reporters.
    """

    def report(self, backup_report: BackupReport) -> Any:
        """
        Submits a backup report and all its subreports.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not provide an implementation"
        )  # pragma: nocover
