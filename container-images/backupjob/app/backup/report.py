"""
backup.report
=============

Contains backup reporting code.
"""

from enum import Enum
from typing import Any, Callable, Generator, Optional, Self, TypeVar


T = TypeVar("T")


class BackupReportFieldAnnotation(Enum):
    """
    Backup report field annotation. Used to provide additional information about a backup field.
    """

    OK = "ok"
    WARNING = "warn"
    ERROR = "error"
    ERROR_UNKNOWN = "error_unknown"

    MULTILINE_TEXT = "multiline_text"


BackupReportFieldAnnotator = Callable[[T], Optional[BackupReportFieldAnnotation]]


class BackupReportField[T]:
    """
    Object representing a backup report field.

    Fields consist of a label and data. They can be annotated by an optional Annotator,
    which provides presentation information about the field.
    """

    def __init__(
        self, label: str, data: T, annotator: Optional[BackupReportFieldAnnotator]
    ) -> None:
        self.label = label
        self.data = data
        self.annotator = annotator

    @property
    def annotation(self) -> Optional[BackupReportFieldAnnotation]:
        """
        Returns the annotation for this backup field.
        """
        if self.annotator is not None:
            return self.annotator(self.data)
        return None

    def __eq__(self, other: Any) -> bool:
        """
        Determines if this field is equivalent to another.
        """
        if not isinstance(other, BackupReportField):
            return False

        return (
            self.label == other.label
            and self.data == other.data
            and self.annotation == other.annotation
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(label={self.label})"


class BackupReport[T]:
    """
    Common interface for reporting backup information.
    """

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.fields: list[BackupReportField] = list()
        self.subreports: list[Self] = list()

        # This is the command execution result that this
        # BackupReport is based on.
        self.result: Optional[T] = None

        # If True, a BackupReport may be excluded from whatever action
        # a backup reporter takes.
        #
        # This can be set to avoid unnecessary noise in case restic or
        # rclone runs end up being a no-op.
        self.omittable = False

        # Whether the backup report indicates a successful operation.
        self.successful = False

    def add_field(self, field: BackupReportField) -> None:
        """
        Adds a field to this backup report.
        """
        self.fields.append(field)

    def add_subreport(self, subreport: Self) -> None:
        """
        Adds a subreport to this backup report.
        """
        self.subreports.append(subreport)

    def find_one_field(
        self,
        filter: Callable[[BackupReportField], bool],
        include_subreports: bool = False,
    ) -> Optional[BackupReportField]:
        """
        Searches for a backup report field matching the given filter. Returns the
        first such field found, or None if no field was found.
        """
        if include_subreports:
            search_reports = self.all_reports()
        else:
            search_reports = [self]

        for report in search_reports:
            for f in report.fields:
                if filter(f):
                    return f

        return None

    def new_field(
        self,
        label: str,
        data: T,
        annotator: Optional[BackupReportFieldAnnotator],
    ) -> BackupReportField[T]:
        """
        Creates a new BackupReportField and adds it to this report.
        """
        field = BackupReportField(label, data, annotator)
        self.add_field(field)
        return field

    def new_subreport(self, name: str) -> Self:
        """
        Creates a new BackupReport and adds it as a subreport of this report.
        """
        subreport = self.__class__(f"{self.name} / {name}")
        self.add_subreport(subreport)
        return subreport

    def all_reports(self) -> Generator[Self]:
        """
        Iterates over all reports contained in this one, including the top level report.
        """
        yield self
        for i in self.subreports:
            for j in i.all_reports():
                yield j
