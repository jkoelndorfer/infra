"""
Tests the ResticClient class.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from backup.restic import (
    InvalidResticRepositoryPasswordError,
    ResticClient,
    ResticError,
)

from testlib.cmd import (
    MockCommandExecutor,
    MockInvokedCommand,
)
from testlib.restic import ExpectedResticCommand


@pytest.fixture
def snapshots_output() -> list[dict]:
    """
    Returns mock output from a `restic snapshots` invocation.
    """
    return [
        {
            "time": "2025-11-02T11:46:27.402512808-06:00",
            "parent": "0000000100000000000000000000000000000000000000000000000000000000",
            "tree": "1000000100000000000000000000000000000000000000000000000000000000",
            "paths": ["/data/src/1"],
            "hostname": "test",
            "username": "root",
            "program_version": "restic 0.18.0",
            "summary": {
                "backup_start": "2025-11-02T11:46:27.402512808-06:00",
                "backup_end": "2025-11-02T11:46:28.231534042-06:00",
                "files_new": 0,
                "files_changed": 0,
                "files_unmodified": 1989,
                "dirs_new": 0,
                "dirs_changed": 865,
                "dirs_unmodified": 18,
                "data_blobs": 0,
                "tree_blobs": 866,
                "data_added": 1016451,
                "data_added_packed": 434650,
                "total_files_processed": 1989,
                "total_bytes_processed": 435508331,
            },
            "id": "0000000200000000000000000000000000000000000000000000000000000000",
            "short_id": "00000002",
        },
    ]


class TestResticClientMockCommandExecutor:
    """
    Contains tests for the ResticClient that use a mock command executor.

    The actual restic binary is not invoked for these tests.
    """

    @pytest.mark.parametrize(
        "source_path",
        [(Path("/home/user/my-backup-data")), (Path("/var/local/important-stuff"))],
    )
    def test_backup(
        self,
        expected_restic_cmd: ExpectedResticCommand,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
        source_path: Path,
    ) -> None:
        """
        Tests that the backup method correctly invokes restic to perform a backup.
        """
        rc = 0
        snapshot_id = "9e920286b898dd7f493dd31413ed689c641bff30cd58a5206b7fa1d500ffe502"
        msg = {
            "message_type": "summary",
            "files_new": 19,
            "files_changed": 0,
            "files_unmodified": 0,
            "dirs_new": 5,
            "dirs_changed": 0,
            "dirs_unmodified": 0,
            "data_blobs": 19,
            "tree_blobs": 6,
            "data_added": 22215,
            "data_added_packed": 10440,
            "total_files_processed": 19,
            "total_bytes_processed": 10549,
            "total_duration": 0.714634746,
            "backup_start": "2025-10-18T19:02:51.792880666-05:00",
            "backup_end": "2025-10-18T19:02:52.507515422-05:00",
            "snapshot_id": snapshot_id,
        }
        mock_cmd_executor.set_result_json_messages(rc, [msg])
        expected_cmd = expected_restic_cmd(
            ["backup", "--skip-if-unchanged", source_path.name]
        )
        expected_invocation = MockInvokedCommand(expected_cmd, source_path.parent)

        result = restic_client_mock_cmd.backup(source_path, True)
        summary = result.summary

        assert summary is not None
        assert summary.snapshot_id == snapshot_id
        assert expected_invocation in mock_cmd_executor.invoked_commands

    def test_check_no_read_data(
        self,
        expected_restic_cmd: ExpectedResticCommand,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
    ) -> None:
        """
        Tests the check method without reading data.
        """
        rc = 0
        msg = {
            "message_type": "summary",
            "num_errors": 0,
            "broken_packs": None,
            "suggest_repair_index": False,
            "suggest_prune": False,
        }
        mock_cmd_executor.set_result_json_messages(rc, messages=[msg])
        expected_cmd = expected_restic_cmd(["check"])

        result = restic_client_mock_cmd.check(read_data=False)
        summary = result.summary

        assert summary is not None
        assert summary.num_errors == 0
        assert expected_cmd in mock_cmd_executor.invoked_commands

    def test_check_with_read_data(
        self,
        expected_restic_cmd: ExpectedResticCommand,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
    ) -> None:
        """
        Tests the check method with read data reading enabled.
        """
        rc = 0
        msg = {
            "message_type": "summary",
            "num_errors": 0,
            "broken_packs": None,
            "suggest_repair_index": False,
            "suggest_prune": False,
        }
        mock_cmd_executor.set_result_json_messages(rc, messages=[msg])
        expected_cmd = expected_restic_cmd(["check", "--read-data"])

        result = restic_client_mock_cmd.check(read_data=True)
        summary = result.summary

        assert summary is not None
        assert summary.num_errors == 0
        assert expected_cmd in mock_cmd_executor.invoked_commands

    def test_repository_is_initialized_executes_correct_command(
        self,
        expected_restic_cmd: ExpectedResticCommand,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
        restic_repository_path: str,
    ) -> None:
        """
        Tests the repository_is_initialized method executes the correct restic command.
        """
        rc_uninitialized = 10
        msg = {
            "message_type": "exit_error",
            "code": rc_uninitialized,
            "message": (
                f"Fatal: repository does not exist: unable to open config file: stat {restic_repository_path}/config: "
                f"no such file or directory\nIs there a repository at the following location?\n{restic_repository_path}"
            ),
        }
        mock_cmd_executor.set_result_json_messages(rc_uninitialized, [msg])

        restic_client_mock_cmd.repository_is_initialized()

        assert (
            expected_restic_cmd(["cat", "config"]) in mock_cmd_executor.invoked_commands
        )

    def test_repository_is_initialized_when_repository_unreadable(
        self,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
        restic_repository_path: str,
    ) -> None:
        """
        Tests the repository_is_initialized method raises an exception when the repository is unreadable.
        """
        rc_unreadable = 1
        msg = {
            "message_type": "exit_error",
            "code": rc_unreadable,
            "message": (
                f"Fatal: unable to open config file: stat {restic_repository_path}/config: permission denied\n"
                f"Is there a repository at the following location?\n{restic_repository_path}"
            ),
        }
        mock_cmd_executor.set_result_json_messages(rc_unreadable, [msg])

        with pytest.raises(ResticError):
            restic_client_mock_cmd.repository_is_initialized()

    def test_repository_is_initialized_when_not_initialized(
        self,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
        restic_repository_path: str,
    ) -> None:
        """
        Tests the repository_is_initialized method when the repository is not initialized.
        """
        rc_uninitialized = 10
        msg = {
            "message_type": "exit_error",
            "code": rc_uninitialized,
            "message": (
                f"Fatal: repository does not exist: unable to open config file: stat {restic_repository_path}/config: "
                f"no such file or directory\nIs there a repository at the following location?\n{restic_repository_path}"
            ),
        }
        mock_cmd_executor.set_result_json_messages(rc_uninitialized, [msg])

        initialized = restic_client_mock_cmd.repository_is_initialized()

        assert not initialized

    def test_repository_is_initialized_when_initialized(
        self,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
    ) -> None:
        """
        Tests the repository_is_initialized method when the repository has been initialized.
        """
        rc_initialized = 0
        msg = {
            "version": 2,
            "id": "21ae9b84e00da78286222c05ce2accd788c737a5bf1865c13bb8f0ba836d3f95",
            "chunker_polynomial": "277ab04be406c1",
        }
        mock_cmd_executor.set_result_json_messages(rc_initialized, [msg])

        initialized = restic_client_mock_cmd.repository_is_initialized()

        assert initialized

    def test_repository_is_initialized_when_password_incorrect(
        self,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
    ) -> None:
        """
        Tests that the repository_is_initialized method raises an exception when the repository
        password is incorrect.
        """
        rc_wrong_password = 12
        msg = {
            "message_type": "exit_error",
            "code": rc_wrong_password,
            "message": "Fatal: wrong password or no key found",
        }
        mock_cmd_executor.set_result_json_messages(rc_wrong_password, [msg])

        with pytest.raises(InvalidResticRepositoryPasswordError):
            restic_client_mock_cmd.repository_is_initialized()

    def test_init_invokes_correct_command(
        self,
        expected_restic_cmd: ExpectedResticCommand,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
        restic_repository_path: str,
    ) -> None:
        """
        Tests that the init method invokes the correct command.
        """
        rc = 0
        msg = {
            "message_type": "initialized",
            "id": "21ae9b84e00da78286222c05ce2accd788c737a5bf1865c13bb8f0ba836d3f95",
            "repository": restic_repository_path,
        }
        mock_cmd_executor.set_result_json_messages(returncode=rc, messages=[msg])

        restic_client_mock_cmd.init()

        assert expected_restic_cmd(["init"]) in mock_cmd_executor.invoked_commands

    def test_init_raises_exception_when_repository_unreadable(
        self,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
        restic_repository_path: str,
    ) -> None:
        """
        Tests that the init method raises an exception when the repository is unreadable.
        """
        rc = 1
        msg = {
            "message_type": "exit_error",
            "code": rc,
            "message": (
                f"Fatal: create repository at {restic_repository_path} failed: "
                f"Fatal: unable to open repository at {restic_repository_path}: mkdir "
                f"{restic_repository_path}/data: permission denied\n",
            ),
        }
        mock_cmd_executor.set_result_json_messages(returncode=rc, messages=[msg])

        with pytest.raises(ResticError):
            restic_client_mock_cmd.init()

    def test_snapshots_returns_snapshot_list(
        self,
        expected_restic_cmd: ExpectedResticCommand,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
        snapshots_output: list[dict],
    ) -> None:
        """
        Tests that the snapshots method returns a list of snapshots with the result.
        """
        rc = 0
        expected_time = datetime(
            2025,
            11,
            2,
            11,
            46,
            27,
            402512,
            tzinfo=timezone(timedelta(days=-1, seconds=64800)),
        )
        expected_backup_start = datetime(
            2025,
            11,
            2,
            11,
            46,
            27,
            402512,
            tzinfo=timezone(timedelta(days=-1, seconds=64800)),
        )
        expected_backup_end = datetime(
            2025,
            11,
            2,
            11,
            46,
            28,
            231534,
            tzinfo=timezone(timedelta(days=-1, seconds=64800)),
        )

        mock_cmd_executor.set_result(
            returncode=rc,
            stdout=json.dumps(snapshots_output).encode("utf-8"),
            stderr=b"",
        )

        result = restic_client_mock_cmd.snapshots()

        assert len(result.snapshots) == 1
        s = result.snapshots[0]
        sm = s.summary

        assert expected_restic_cmd(["snapshots"]) in mock_cmd_executor.invoked_commands
        assert s.time == expected_time
        assert (
            s.parent
            == "0000000100000000000000000000000000000000000000000000000000000000"
        )
        assert (
            s.tree == "1000000100000000000000000000000000000000000000000000000000000000"
        )
        assert s.paths == [Path("/data/src/1")]
        assert s.hostname == "test"
        assert s.username == "root"
        assert s.program_version == "restic 0.18.0"
        assert (
            s.id == "0000000200000000000000000000000000000000000000000000000000000000"
        )
        assert s.short_id == "00000002"
        assert sm.backup_start == expected_backup_start
        assert sm.backup_end == expected_backup_end
        assert sm.files_new == 0
        assert sm.files_changed == 0
        assert sm.files_unmodified == 1989
        assert sm.dirs_new == 0
        assert sm.dirs_changed == 865
        assert sm.dirs_unmodified == 18
        assert sm.data_blobs == 0
        assert sm.tree_blobs == 866
        assert sm.data_added == 1016451
        assert sm.data_added_packed == 434650
        assert sm.total_files_processed == 1989
        assert sm.total_bytes_processed == 435508331

    @pytest.mark.parametrize("latest", [1, 2])
    def test_snapshots_passes_latest_with_latest_arg(
        self,
        expected_restic_cmd: ExpectedResticCommand,
        mock_cmd_executor: MockCommandExecutor,
        restic_client_mock_cmd: ResticClient,
        snapshots_output: list[dict],
        latest: int,
    ) -> None:
        """
        Ensures that the restic client passes the --latest option with
        a parameter when latest is passed to the snapshots method.
        """
        rc = 0
        mock_cmd_executor.set_result(
            returncode=rc,
            stdout=json.dumps(snapshots_output).encode("utf-8"),
            stderr=b"",
        )
        restic_client_mock_cmd.snapshots(latest=latest)

        assert (
            expected_restic_cmd(["snapshots", "--latest", str(latest)])
            in mock_cmd_executor.invoked_commands
        )
