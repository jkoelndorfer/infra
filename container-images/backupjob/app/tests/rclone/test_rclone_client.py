"""
Tests the RcloneClient class.
"""

from pathlib import Path

from backup.rclone import RcloneClient

from testlib.cmd import MockCommandExecutor


class TestRcloneClientMockCommandExecutor:
    """
    Contains tests for the RcloneClient that use a mock command executor.

    The actual rclone binary is not invoked for these tests.
    """

    def test_sync(
        self,
        mock_cmd_executor: MockCommandExecutor,
        rclone_client_mock_cmd: RcloneClient,
        rclone_source_dir: Path,
        rclone_destination_dir: Path,
    ) -> None:
        """
        Tests the sync method.
        """
        rclone_client_mock_cmd.provider_args = ["--s3-provider", "AWS"]
        rclone_client_mock_cmd.sync_args = ["--bwlimit", "00:00 off"]
        mock_cmd_executor.set_result_json_messages(
            0,
            [
                {
                    "time": "2025-10-26T21:32:13.618828486-05:00",
                    "level": "notice",
                    "msg": 'Config file "/home/user/.config/rclone/rclone.conf" not found - using defaults',
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.620064951-05:00",
                    "level": "info",
                    "msg": "Copied (new)",
                    "size": 64,
                    "object": "data1",
                    "objectType": "*local.Object",
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.620121721-05:00",
                    "level": "info",
                    "msg": "Copied (new)",
                    "size": 64,
                    "object": "data2",
                    "objectType": "*local.Object",
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.62017003-05:00",
                    "level": "info",
                    "msg": "Copied (new)",
                    "size": 64,
                    "object": "data3",
                    "objectType": "*local.Object",
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.62020373-05:00",
                    "level": "info",
                    "msg": "Copied (new)",
                    "size": 64,
                    "object": "data5",
                    "objectType": "*local.Object",
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.62021938-05:00",
                    "level": "info",
                    "msg": "Copied (new)",
                    "size": 64,
                    "object": "data4",
                    "objectType": "*local.Object",
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.620238049-05:00",
                    "level": "info",
                    "msg": "Copied (new)",
                    "size": 64,
                    "object": "data6",
                    "objectType": "*local.Object",
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.620279229-05:00",
                    "level": "info",
                    "msg": "Copied (new)",
                    "size": 64,
                    "object": "data7",
                    "objectType": "*local.Object",
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.620298829-05:00",
                    "level": "info",
                    "msg": "Copied (new)",
                    "size": 64,
                    "object": "data8",
                    "objectType": "*local.Object",
                    "source": "slog/logger.go:256",
                },
                {
                    "time": "2025-10-26T21:32:13.620334868-05:00",
                    "level": "info",
                    "msg": "\nTransferred:   \t        512 B / 512 B, 100%, 0 B/s, ETA -\nChecks:                 0 / 0, -, Listed 8\nTransferred:            8 / 8, 100%\nElapsed time:         0.0s\n\n",
                    "stats": {
                        "bytes": 512,
                        "checks": 0,
                        "deletedDirs": 0,
                        "deletes": 0,
                        "elapsedTime": 0.000775391,
                        "errors": 0,
                        "eta": None,
                        "fatalError": False,
                        "listed": 8,
                        "renames": 0,
                        "retryError": False,
                        "serverSideCopies": 0,
                        "serverSideCopyBytes": 0,
                        "serverSideMoveBytes": 0,
                        "serverSideMoves": 0,
                        "speed": 0,
                        "totalBytes": 512,
                        "totalChecks": 0,
                        "totalTransfers": 8,
                        "transferTime": 0.000470385,
                        "transfers": 8,
                    },
                    "source": "slog/logger.go:256",
                },
            ],
        )
        expected_cmd = [
            "rclone",
            "--verbose",
            "--use-json-log",
            "--s3-provider",
            "AWS",
            "sync",
            "--bwlimit",
            "00:00 off",
            str(rclone_source_dir),
            str(rclone_destination_dir),
        ]

        sync_result = rclone_client_mock_cmd.sync(
            str(rclone_source_dir), str(rclone_destination_dir)
        )

        assert expected_cmd in mock_cmd_executor.invoked_commands
        assert sync_result.stats.bytes == 512
        assert sync_result.stats.deletes == 0
        assert sync_result.stats.errors == 0
        assert sync_result.stats.transfers == 8
