"""
testlib.backupsrc
=================

Contains models representing information about test backup sources.
"""

from functools import reduce
from pathlib import Path


class BackupSourceSubdirectory:
    """
    Object containing information about a top-level backup subdirectory.
    """

    def __init__(self, path: Path, count: int, size: int) -> None:
        self.path = path
        self.count = count
        self.file_size = size

    @property
    def total_size(self) -> int:
        """
        The total size of all files in this directory.
        """
        return self.count * self.file_size


class BackupSourceInfo:
    """
    Containing information about the backup source directory used for testing.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.directories: list[BackupSourceSubdirectory] = list()

    @property
    def total_top_level_backup_targets(self) -> int:
        """
        The total number of top level backup targets in the backup source directory.
        """
        return len(self.directories)

    @property
    def total_count(self) -> int:
        """
        The total number of files in the backup source directory.
        """
        return reduce(lambda x, y: x + y.count, self.directories, 0)

    @property
    def total_size(self) -> int:
        """
        The total data in the backup source directory.
        """
        return reduce(lambda x, y: x + y.total_size, self.directories, 0)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(path={self.path}, "
            f"total_count={self.total_count}, "
            f"total_size={self.total_size})"
        )
