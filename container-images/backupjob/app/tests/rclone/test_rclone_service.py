"""
Tests the RcloneService class.
"""

from pathlib import Path

import pytest

from backup.rclone import RcloneClient, RcloneService

from testlib import BackupSourceInfo


@pytest.fixture
def rclone_service(rclone_client: RcloneClient) -> RcloneService:
    """
    RcloneService using a real RcloneClient.

    Method calls made to the RcloneService will invoke the rclone binary
    and copy real files around.
    """
    return RcloneService(client=rclone_client)


class TestRcloneService:
    """
    Contains tests for the RcloneService.
    """

    def test_sync(
        self,
        backup_src_info: BackupSourceInfo,
        rclone_destination_dir: Path,
        rclone_service: RcloneService,
    ) -> None:
        """
        Tests the sync method.
        """
        report = rclone_service.sync(
            "test_sync", str(backup_src_info.path), str(rclone_destination_dir)
        )

        source = report.find_one_field(lambda f: f.label == "Source")
        destination = report.find_one_field(lambda f: f.label == "Destination")
        bytes_transferred = report.find_one_field(
            lambda f: f.label == "Bytes Transferred"
        )
        files_transferred = report.find_one_field(
            lambda f: f.label == "Files Transferred"
        )
        deletes = report.find_one_field(lambda f: f.label == "Deletes")

        assert source is not None
        assert destination is not None
        assert bytes_transferred is not None
        assert files_transferred is not None
        assert deletes is not None

        assert source.data == str(backup_src_info.path)
        assert destination.data == str(rclone_destination_dir)
        assert bytes_transferred.data == backup_src_info.total_size
        assert files_transferred.data == backup_src_info.total_count
        assert deletes.data == 0
