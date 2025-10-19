"""
Common Restic configuration for backup tests.
"""

from pathlib import Path

import pytest

from backup.cmd import CommandExecutorProtocol, cmdexec
from backup.restic import ResticClient

from testlib.restic import ExpectedResticCommand


@pytest.fixture
def expected_restic_cmd(
    restic_repository_path: str, restic_password_file: Path, restic_cache_dir: Path
) -> ExpectedResticCommand:
    """
    Helper function that, when given a subcommand returns the full expected restic command invocation.
    """

    def f(cmd: list[str]) -> list[str]:
        return [
            "restic",
            "--repo",
            restic_repository_path,
            "--cache-dir",
            str(restic_cache_dir),
            "--password-file",
            str(restic_password_file),
            "--json",
            *cmd,
        ]

    return f


@pytest.fixture
def restic_client(
    restic_repository_path: str,
    restic_password_file: Path,
    restic_cache_dir: Path,
) -> ResticClient:
    """
    ResticClient using a real command executor. Methods called on this client will
    invoke the restic binary.
    """
    return ResticClient(
        cmdexec=cmdexec,
        repository_path=restic_repository_path,
        password_file=restic_password_file,
        cache_dir=restic_cache_dir,
    )


@pytest.fixture
def restic_client_mock_cmd(
    mock_cmd_executor: CommandExecutorProtocol,
    restic_repository_path: str,
    restic_password_file: Path,
    restic_cache_dir: Path,
) -> ResticClient:
    """
    ResticClient using a mock command executor. Methods called on
    this client will *not* invoke the restic binary.
    """
    return ResticClient(
        cmdexec=mock_cmd_executor,
        repository_path=restic_repository_path,
        password_file=restic_password_file,
        cache_dir=restic_cache_dir,
    )


@pytest.fixture
def restic_dir(tmpdir: Path) -> Path:
    """
    Path to a directory used containing restic-related test data.
    """
    d = tmpdir / "restic"
    d.mkdir()

    return d


@pytest.fixture
def restic_cache_dir(restic_dir: Path) -> Path:
    """
    Path to an empty Restic cache directory.
    """
    return restic_dir / "cache"


@pytest.fixture
def restic_repository_path(restic_dir: Path) -> str:
    """
    Path to a temporary directory that can be used to initialize a Restic repository.
    """
    return str(restic_dir / "repo")


@pytest.fixture
def restic_password_file(restic_dir: Path) -> Path:
    """
    Contains the path to a password file that can be used to initialize
    a new restic repository.
    """
    p = restic_dir / "password"

    with open(p, "w") as f:
        f.write("test-repo-password")

    return p
