"""
Common Rclone configuration for backup tests.
"""

from pathlib import Path

import pytest

from backup.cmd import cmdexec
from backup.rclone import RcloneClient

from testlib.cmd import MockCommandExecutor


@pytest.fixture
def sync_destination(tmpdir: Path) -> Path:
    """
    Destination for rclone syncs.
    """
    return tmpdir / "rclone-dest"


@pytest.fixture
def rclone_client() -> RcloneClient:
    """
    RcloneClient using a real command executor. Methods called on this client will
    invoke the rclone binary.
    """
    return RcloneClient(cmdexec=cmdexec)


@pytest.fixture
def rclone_client_mock_cmd(mock_cmd_executor: MockCommandExecutor) -> RcloneClient:
    """
    RcloneClient using a mock command executor. Methods called on
    this client will *not* invoke the rclone binary.
    """
    return RcloneClient(cmdexec=mock_cmd_executor)


@pytest.fixture
def rclone_dir(tmpdir: Path) -> Path:
    """
    Path to a temporary directory that can be used for rclone testing.
    """
    d = tmpdir / "rclone"
    d.mkdir()

    return d


@pytest.fixture
def rclone_source_dir(rclone_dir: Path) -> Path:
    """
    Path to a temporary directory that can be used as an rclone source.
    """
    d = rclone_dir / "source"
    d.mkdir()

    return d


@pytest.fixture
def rclone_destination_dir(rclone_dir: Path) -> Path:
    """
    Path to a temporary directory that can be used as an rclone destination.
    """
    d = rclone_dir / "destination"
    d.mkdir()

    return d
