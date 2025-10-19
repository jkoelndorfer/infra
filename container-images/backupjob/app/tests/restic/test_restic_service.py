"""
Tests the ResticService class.
"""

from os import geteuid
from pathlib import Path

import pytest

from backup.restic import ResticClient, ResticService

from testlib import BackupSourceInfo


@pytest.fixture
def restic_service(restic_client: ResticClient) -> ResticService:
    """
    ResticService using a real ResticClient.

    Method calls made to the ResticService will invoke the restic binary
    and perform operations against a real repository.
    """
    return ResticService(restic_client)


class TestResticServiceIntegration:
    """
    Tests the ResticService class where the underlying client performs operations
    using the restic binary against an actual backup repository.
    """

    def test_backup_init_fail(
        self,
        backup_src_info: BackupSourceInfo,
        restic_dir: Path,
        restic_service: ResticService,
    ) -> None:
        """
        Tests backing up a directory when repository initialization fails.
        """
        if geteuid() == 0:
            # This test will not pass when run as root.
            #
            # It relies on using chmod to limit permissions on
            # the restic directory. The root user skips those
            # access checks.
            pytest.xfail("test does not pass when run as root")

        # Make the restic directory non-writable so repository initialization will fail.
        restic_dir.chmod(0o500)

        report = restic_service.backup(
            name="test_backup_init_fail",
            source=backup_src_info.path,
            for_each=False,
            skip_if_unchanged=False,
        )
        init_ok = report.find_one_field(lambda f: f.label == "Init OK")

        assert init_ok is not None
        assert init_ok.data is False

        restic_dir.chmod(0o700)

    def test_backup_single_directory_uninitialized_repo(
        self, backup_src_info: BackupSourceInfo, restic_service: ResticService
    ) -> None:
        """
        Tests backing up a single directory, setting for_each = False, with a new, uninitialized repository.
        """
        report = restic_service.backup(
            name="test_backup_single_directory_uninitialized_repo",
            source=backup_src_info.path,
            for_each=False,
            skip_if_unchanged=False,
        )

        new_repo = report.find_one_field(lambda f: f.label == "New Repo")
        new_files = report.find_one_field(lambda f: f.label == "New Files")
        total_bytes_processed = report.find_one_field(
            lambda f: f.label == "Total Bytes Processed"
        )

        assert new_files is not None
        assert total_bytes_processed is not None
        assert new_repo is not None
        assert new_files.data == backup_src_info.total_count
        assert total_bytes_processed.data == backup_src_info.total_size
        assert new_repo.data is True

    def test_backup_each_directory_uninitialized_repo(
        self, backup_src_info: BackupSourceInfo, restic_service: ResticService
    ) -> None:
        """
        Tests backing up a directory, setting for_each = True, with a new, uninitialized repository.
        """
        report = restic_service.backup(
            name="test_backup_each_directory_uninitialized_repo",
            source=backup_src_info.path,
            for_each=True,
            skip_if_unchanged=False,
        )
        total_count = 0
        total_bytes_processed = 0

        all_reports = list(report.all_reports())

        assert len(all_reports) == backup_src_info.total_top_level_backup_targets + 1

        for r in all_reports:
            new_files = r.find_one_field(lambda f: f.label == "New Files")
            processed_data = r.find_one_field(
                lambda f: f.label == "Total Bytes Processed"
            )
            if new_files is not None:
                total_count += new_files.data
            if processed_data is not None:
                total_bytes_processed += processed_data.data

        assert total_count == backup_src_info.total_count
        assert total_bytes_processed == backup_src_info.total_size

    def test_backup_backup_fail(
        self,
        backup_src_info: BackupSourceInfo,
        restic_service: ResticService,
    ) -> None:
        """
        Tests backing up a directory where initialization is successful, but the backup fails.
        """
        if geteuid() == 0:
            # This test will not pass when run as root.
            #
            # It relies on using chmod to limit permissions on
            # the restic directory. The root user skips those
            # access checks.
            pytest.xfail("test does not pass when run as root")

        backup_src_info.path.chmod(0o200)

        report = restic_service.backup(
            name="test_backup_backup_fail",
            source=backup_src_info.path,
            for_each=False,
            skip_if_unchanged=False,
        )

        error = report.find_one_field(lambda f: f.label == "Error")
        backup_ok = report.find_one_field(lambda f: f.label == "Backup OK")

        assert error is not None
        assert backup_ok is not None
        assert backup_ok.data is False

        backup_src_info.path.chmod(0o700)

    def test_check(
        self, backup_src_info: BackupSourceInfo, restic_service: ResticService
    ) -> None:
        """
        Performs a test backup, then performs a repository check.
        """
        restic_service.backup(
            name="test_check",
            source=backup_src_info.path,
            for_each=False,
            skip_if_unchanged=False,
        )
        check_report = restic_service.check()

        errors = check_report.find_one_field(lambda f: f.label == "Errors")
        repair_suggested = check_report.find_one_field(
            lambda f: f.label == "Repair Suggested"
        )
        prune_suggested = check_report.find_one_field(
            lambda f: f.label == "Prune Suggested"
        )

        assert errors is not None
        assert repair_suggested is not None
        assert prune_suggested is not None
        assert errors.data == 0
        assert repair_suggested.data is False
        assert prune_suggested.data is False
