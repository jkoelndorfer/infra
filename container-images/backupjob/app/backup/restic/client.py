"""
backup.restic.client
====================

Contains the implementation for the restic client.
"""

import json
from pathlib import Path
from typing import Optional, Type, TypeVar

from ..cmd import CommandExecutorProtocol
from ..log import logger
from .error import ResticError, InvalidResticRepositoryPasswordError
from .model import ResticResult, ResticBackupResult, ResticCheckResult, ResticReturnCode


RR = TypeVar("RR", bound=ResticResult)


class ResticClient:
    """
    Client to the restic binary.

    This client provides only a subset of functionality needed to execute and verify backups.
    """

    def __init__(
        self,
        cmdexec: CommandExecutorProtocol,
        repository_path: str,
        password_file: Optional[Path],
        cache_dir: Optional[Path],
    ) -> None:
        self.cmdexec = cmdexec
        self.log = logger("restic.ResticClient")
        self.repository_path = repository_path
        self.password_file = password_file
        self.cache_dir = cache_dir

    def repository_is_initialized(self) -> bool:
        """
        Convenience function that determines if a repository has been initialized according to
        https://restic.readthedocs.io/en/stable/075_scripting.html#exit-codes.
        """
        result = self.run(
            "cat", "config", result_type=ResticResult, single_json_document=True
        )

        # See https://restic.readthedocs.io/en/stable/075_scripting.html#exit-codes.
        match result.returncode:
            case ResticReturnCode.RC_REPOSITORY_INITIALIZED:
                return True

            case ResticReturnCode.RC_REPOSITORY_NOT_INITIALIZED:
                return False

            case ResticReturnCode.RC_BAD_REPOSITORY_PASSWORD:
                raise InvalidResticRepositoryPasswordError(
                    "invalid repository password", result
                )

            case _:
                # Unhandled error.
                for m in result.messages:
                    self.log.error(f"restic error: {str(m)}")
                raise ResticError("unhandled error from restic", result)

    def backup(self, source: Path, skip_if_unchanged: bool) -> ResticBackupResult:
        """
        Performs a restic backup for the given source directory.
        """
        optional_args: list[str] = list()
        if skip_if_unchanged:
            optional_args.append("--skip-if-unchanged")

        # Here, we force use of relative paths. Using absolute paths means that if any
        # parent directory metadata changes, restic will produce a new snapshot [1],
        # which is almost certainly not what we want -- especially since this will
        # be running in a container via Kubernetes.
        return self.run(
            "backup",
            *optional_args,
            str(source.name),
            result_type=ResticBackupResult,
            cwd=source.parent,
            single_json_document=False,
        )

    def check(self, read_data: bool) -> ResticCheckResult:
        """
        Performs a repository check.
        """
        optional_args: list[str] = list()

        if read_data:
            optional_args.append("--read-data")

        return self.run(
            "check",
            *optional_args,
            result_type=ResticCheckResult,
            single_json_document=False,
        )

    def full_cmd(self, *subcmd: str) -> list[str]:
        """
        Given a restic subcommand (e.g. `cat config` or `backup /path/to/source`), returns the
        full restic command to be invoked, including arguments that specify the repository path
        and path to the password file, among others.
        """
        cmd_common: list[str] = ["restic", "--repo", self.repository_path]

        if self.cache_dir is not None:
            cmd_common.extend(["--cache-dir", str(self.cache_dir)])

        if self.password_file is not None:
            cmd_common.extend(["--password-file", str(self.password_file)])

        cmd_common.append("--json")

        return [*cmd_common, *subcmd]

    def init(self) -> ResticResult:
        """
        Initializes the repository.
        """
        result = self.run("init", result_type=ResticResult, single_json_document=False)
        if result.returncode != ResticReturnCode.RC_OK:
            raise ResticError("failed initializing repository", result)
        return result

    def run(
        self,
        *cmd: str,
        result_type: Type[RR],
        single_json_document: bool,
        cwd: Optional[Path] = None,
    ) -> RR:
        """
        Runs restic with the given command, returning all the messages produced by restic.
        """
        if cwd is None:
            cwd = Path.cwd()
        assert isinstance(cwd, Path)

        full_cmd = self.full_cmd(*cmd)
        proc = self.cmdexec(full_cmd, cwd=cwd, combine_stdout_stderr=True)
        if single_json_document:
            messages = [json.loads(proc.stdout)]
        else:
            messages = list(
                map(lambda ln: json.loads(ln), proc.stdout.splitlines(b"\n"))
            )

        return result_type(
            repository=self.repository_path,
            cmd=list(cmd),
            full_cmd=full_cmd,
            returncode=proc.returncode,
            messages=messages,
        )
