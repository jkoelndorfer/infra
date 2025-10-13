"""
Global test configuration for backup tests.
"""

from pathlib import Path
import shutil
from tempfile import mkdtemp
from typing import Generator

import pytest

from testlib import MockCommandExecutor


@pytest.fixture
def mock_cmd_executor() -> MockCommandExecutor:
    """
    Mock command executor. Commands are not actually executed using this executor.
    """
    return MockCommandExecutor()


@pytest.fixture
def tmpdir() -> Generator[Path]:
    """
    Temporary directory that tests can use to store data.
    """
    d = Path(mkdtemp(prefix="backupjob-tests-"))

    yield d

    shutil.rmtree(d, ignore_errors=True)
