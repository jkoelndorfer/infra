"""
Tests the ResticService class.
"""

from os import geteuid
from pathlib import Path

import pytest

from backup.cmd import cmdexec
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
            exclude_files=[],
        )
        init_ok = report.find_one_field(lambda f: f.label == "Init OK")

        assert not report.successful
        assert report.result is not None
        assert report.result.returncode != 0
        assert init_ok is not None
        assert init_ok.data is False

        restic_dir.chmod(0o700)

    @pytest.mark.slow
    def test_backup_with_ignore(
        self,
        backup_src_info: BackupSourceInfo,
        restic_service: ResticService,
    ) -> None:
        """
        Tests running a backup with an ignore file.

        All files are ignored except for one -- the ignore file itself.
        """

        for d in backup_src_info.directories:
            with open(
                backup_src_info.path
                / d.path
                / restic_service.implicit_exclude_file_name,
                "w",
            ) as f:
                f.write("backupjob-datagen-*\n")

        report = restic_service.backup(
            name="test_backup_with_ignore",
            source=backup_src_info.path,
            for_each=True,
            skip_if_unchanged=True,
            exclude_files=[],
        )

        all_reports = list(report.all_reports())

        for r in all_reports[1:]:
            new_files = r.find_one_field(lambda f: f.label == "New Files")

            assert new_files is not None
            assert new_files.data == 1

    @pytest.mark.slow
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
            exclude_files=[],
        )

        new_repo = report.find_one_field(lambda f: f.label == "New Repo")
        new_files = report.find_one_field(lambda f: f.label == "New Files")
        total_bytes_processed = report.find_one_field(
            lambda f: f.label == "Total Bytes Processed"
        )

        assert report.successful
        assert new_files is not None
        assert total_bytes_processed is not None
        assert new_repo is not None
        assert new_files.data == backup_src_info.total_count
        assert total_bytes_processed.data == backup_src_info.total_size
        assert new_repo.data is True

    @pytest.mark.slow
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
            exclude_files=[],
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
        assert all(r.successful for r in all_reports)

    @pytest.mark.slow
    def test_double_backup_omittable_reports(
        self, backup_src_info: BackupSourceInfo, restic_service: ResticService
    ) -> None:
        """
        Tests that backing up directories with no changes to ensure that the
        directories without changes have reports where omittable is True.
        """
        restic_service.backup(
            name="test_double_backup_omittable_reports_first",
            source=backup_src_info.path,
            for_each=True,
            skip_if_unchanged=True,
            exclude_files=[],
        )
        report = restic_service.backup(
            name="test_double_backup_omittable_reports_second",
            source=backup_src_info.path,
            for_each=True,
            skip_if_unchanged=True,
            exclude_files=[],
        )

        all_reports = list(report.all_reports())
        omittable_reports = list(filter(lambda r: r.omittable, all_reports))
        num_reports = len(all_reports)

        # The top level "summary" report is always produced.
        #
        # Reports for each of the individual, backed-up directories
        # are excluded if no data has changed.
        expected_num_omitted_reports = num_reports - 1

        assert len(all_reports) == 4
        assert len(omittable_reports) == expected_num_omitted_reports

    @pytest.mark.slow
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
            exclude_files=[],
        )

        error = report.find_one_field(lambda f: f.label == "Error")

        assert not report.successful
        assert report.result is not None
        assert report.result.returncode != 0
        assert error is not None

        backup_src_info.path.chmod(0o700)

    @pytest.mark.slow
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
            exclude_files=[],
        )
        check_report = restic_service.check()

        errors = check_report.find_one_field(lambda f: f.label == "Errors")
        repair_suggested = check_report.find_one_field(
            lambda f: f.label == "Repair Suggested"
        )
        prune_suggested = check_report.find_one_field(
            lambda f: f.label == "Prune Suggested"
        )

        assert check_report.successful
        assert errors is not None
        assert repair_suggested is not None
        assert prune_suggested is not None
        assert errors.data == 0
        assert repair_suggested.data is False
        assert prune_suggested.data is False

    @pytest.mark.slow
    def test_check_failure(
        self,
        backup_src_info: BackupSourceInfo,
        restic_service: ResticService,
        restic_repository_path: str,
    ) -> None:
        """
        Performs a test backup, then makes the repository unreadable, then performs a check.

        This tests the case where a restic check fails.
        """
        repo = Path(restic_repository_path)
        restic_service.backup(
            name="test_check_failure",
            source=backup_src_info.path,
            for_each=False,
            skip_if_unchanged=False,
            exclude_files=[],
        )

        repo.chmod(0o000)
        try:
            check_report = restic_service.check()

            assert not check_report.successful
            assert check_report.result is not None
            assert check_report.result.returncode != 0
        finally:
            repo.chmod(0o700)

    def test_compare_latest_snapshots_same_client(
        self, backup_src_info: BackupSourceInfo, restic_service: ResticService
    ) -> None:
        """
        Tests compare_latest_snapshots using the same restic client as both
        the local and remote client.
        """
        restic_service.backup(
            name="test_compare_latest_snapshots_same_client",
            source=backup_src_info.path,
            for_each=False,
            skip_if_unchanged=False,
            exclude_files=[],
        )
        compare_report = restic_service.compare_latest_snapshots(restic_service.client)
        local_snap_id = compare_report.find_one_field(
            lambda f: f.label == "Local Snapshot ID"
        )
        remote_snap_id = compare_report.find_one_field(
            lambda f: f.label == "Remote Snapshot ID"
        )

        assert compare_report.successful
        assert local_snap_id is not None
        assert remote_snap_id is not None
        assert local_snap_id.data == remote_snap_id.data

    @pytest.mark.slow
    def test_compare_latest_snapshots_different_repositories(
        self,
        backup_src_info: BackupSourceInfo,
        restic_remote_cache_dir: Path,
        restic_remote_repository_path: str,
        restic_password_file: Path,
        restic_service: ResticService,
    ) -> None:
        """
        Tests compare_latest_snapshots when the local and remote repositories are different.
        """
        remote_restic_client = ResticClient(
            cmdexec,
            restic_remote_repository_path,
            restic_password_file,
            restic_remote_cache_dir,
        )
        remote_restic_service = ResticService(remote_restic_client)

        restic_service.backup(
            name="test_compare_latest_snapshots_different_repositories_local",
            source=backup_src_info.path,
            for_each=False,
            skip_if_unchanged=False,
            exclude_files=[],
        )
        remote_restic_service.backup(
            name="test_compare_latest_snapshots_different_repositories_remote",
            source=backup_src_info.path,
            for_each=False,
            skip_if_unchanged=False,
            exclude_files=[],
        )

        report = restic_service.compare_latest_snapshots(remote_restic_client)
        local_snap_id = report.find_one_field(lambda f: f.label == "Local Snapshot ID")
        remote_snap_id = report.find_one_field(
            lambda f: f.label == "Remote Snapshot ID"
        )

        assert not report.successful
        assert local_snap_id is not None
        assert remote_snap_id is not None
        assert local_snap_id.data != remote_snap_id.data
