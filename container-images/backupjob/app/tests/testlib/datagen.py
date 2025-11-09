"""
testlib.datagen
===============

Contains code to generate random data that can be used as a source
dataset for testing backups.
"""

from os import write
from random import randbytes
from tempfile import mkstemp
from pathlib import Path


class DataGenerator:
    """
    Generates files containing random data inside a given root directory.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def generate_random(self, subdirectory: Path, count: int, size: int) -> None:
        """
        Generates `count` files in the given `subdirectory`. Each file is `size` bytes.
        """
        if subdirectory.is_absolute():
            raise ValueError("subdirectory must be a relative path")

        d = self.root / subdirectory
        d.mkdir(parents=True, exist_ok=True)

        for _ in range(count):
            fd, _ = mkstemp(prefix="backupjob-datagen-", dir=d)
            write(fd, randbytes(size))
