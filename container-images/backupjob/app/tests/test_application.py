"""
Tests the backup commandline application.
"""

from os import environ
from pathlib import Path
import random
from string import ascii_letters, digits
from typing import Generator

import pytest

from backup.application import BackupApplication

from testlib.backupsrc import BackupSourceInfo


@pytest.fixture
def backup_app_dir(tmpdir: Path) -> Path:
    """
    Path to a temporary directory for backup application test data.
    """
    d = tmpdir / "backup-app"
    d.mkdir(parents=True, exist_ok=True)

    return d


@pytest.fixture
def restic_backup_source(backup_app_dir: Path) -> Path:
    """
    Path to the source directory for restic backups.
    """
    d = backup_app_dir / "source"
    d.mkdir(parents=True, exist_ok=True)

    return d


@pytest.fixture
def restic_repository(backup_app_dir: Path) -> Path:
    """
    Path to the restic test repository.
    """
    d = backup_app_dir / "restic-repository"
    d.mkdir(parents=True, exist_ok=True)

    return d


@pytest.fixture
def restic_password() -> str:
    """
    Password for the restic repository.
    """
    chars = ascii_letters + digits
    return "".join(random.choice(chars) for _ in range(32))


@pytest.fixture
def restic_password_file(backup_app_dir: Path, restic_password: str) -> Path:
    """
    Path to the restic repository password file.
    """
    password_file = backup_app_dir / "password-file"

    with open(password_file, "w") as f:
        f.write(restic_password)

    return password_file


@pytest.fixture
def restic_cache_dir(backup_app_dir: Path) -> Path:
    """
    Path to the restic cache directory.
    """
    d = backup_app_dir / "restic-cache"
    d.mkdir(parents=True, exist_ok=True)

    return d


@pytest.fixture
def unset_google_chat_webhook_url() -> Generator[None]:
    """
    Fixture that ensures that GOOGLE_CHAT_WEBHOOK_URL is not set
    in the environment.
    """
    k = "GOOGLE_CHAT_WEBHOOK_URL"
    initial = environ.get(k, None)

    try:
        del environ[k]
    except KeyError:
        # The environment variable is already unset.
        pass

    yield

    if initial is not None:
        environ[k] = initial


@pytest.mark.live
class TestBackupApplicationIntegration:
    """
    Performs full, end-to-end tests of the backup application's functionality.
    """

    @pytest.mark.slow
    def test_full_backup_job(
        self,
        backup_src_info: BackupSourceInfo,
        restic_backup_source: Path,
        restic_cache_dir: Path,
        restic_password_file: Path,
        restic_repository: Path,
    ) -> None:
        """
        Tests an rclone sync, restic backup, and restic check.
        """

        if environ.get("GOOGLE_CHAT_WEBHOOK_URL", None) is None:
            pytest.skip(
                "GOOGLE_CHAT_WEBHOOK_URL must be set to run test_full_backup_job"
            )

        rclone_sync_app = BackupApplication()
        restic_backup_app = BackupApplication()
        restic_check_app = BackupApplication()

        rclone_sync_app.main(
            [
                "--name",
                "Data Sync",
                "--reporter",
                "googlechat",
                "rclone",
                "sync",
                str(backup_src_info.path),
                str(restic_backup_source),
            ]
        )

        restic_backup_app.main(
            [
                "--name",
                "Data Backup",
                "--reporter",
                "googlechat",
                "restic",
                "--repository",
                str(restic_repository),
                "--cache-dir",
                str(restic_cache_dir),
                "--password-file",
                str(restic_password_file),
                "backup",
                str(restic_backup_source),
            ]
        )

        restic_check_app.main(
            [
                "--name",
                "Repository Check",
                "--reporter",
                "googlechat",
                "restic",
                "--repository",
                str(restic_repository),
                "--cache-dir",
                str(restic_cache_dir),
                "--password-file",
                str(restic_password_file),
                "check",
            ]
        )

    @pytest.mark.usefixtures("unset_google_chat_webhook_url")
    def test_exception_without_google_chat_url(
        self,
        backup_src_info: BackupSourceInfo,
        restic_backup_source: Path,
    ) -> None:
        """
        Tests that the application raises an exception when there is no
        Google Chat webhook URL specified.
        """
        rclone_sync_app = BackupApplication()

        with pytest.raises(ValueError):
            rclone_sync_app.main(
                [
                    "--name",
                    "Data Sync",
                    "--reporter",
                    "googlechat",
                    "rclone",
                    "sync",
                    str(backup_src_info.path),
                    str(restic_backup_source),
                ]
            )
