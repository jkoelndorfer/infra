"""
backup.application
==================

Contains implementation for the BackupApplication.

The BackupApplication is invoked by the backup script to perform backups.
"""

from argparse import ArgumentParser, Namespace, _SubParsersAction
from logging import INFO, StreamHandler
from os import environ
from pathlib import Path
from sys import stderr
from typing import Optional

from requests import Session

from .cmd import cmdexec
from .log import logger
from .rclone import RcloneClient, RcloneService
from .restic import ResticClient, ResticService
from .reporter import BackupReporter, GoogleChatBackupReporter, GoogleChatReportRenderer
from .report import BackupReport


class BackupApplication:
    """
    Application to perform backups.

    The backup script that is invoked is a thin wrapper around this class.
    """

    RC_OK = 0
    RC_BACKUP_ERROR = 20

    def __init__(self) -> None:
        # Used for validation during test runs.
        self.backup_report: Optional[BackupReport] = None

    def argparser(self) -> ArgumentParser:
        """
        Returns a configured argument parser for this application.
        """
        a = ArgumentParser()
        a.add_argument(
            "--reporter",
            action="store",
            type=str,
            choices=["googlechat"],
            required=True,
            help="The implementation to use for backup reporting.",
        )
        a.add_argument(
            "--name",
            action="store",
            type=str,
            required=True,
            help="The name of the backup (used during reporting).",
        )
        backup_mode = a.add_subparsers(help="type of backup to perform")

        self.argparser_rclone(backup_mode)
        self.argparser_restic(backup_mode)

        return a

    def argparser_rclone(self, a: _SubParsersAction) -> None:
        """
        Configures the rclone arguments for the argument parser.
        """
        rclone = a.add_parser("rclone", help="rclone operations")
        rclone.add_argument(
            "--bwlimit",
            action="store",
            type=str,
            default="off",
            help="the bwlimit to pass to rclone",
        )
        rclone.add_argument(
            "--s3-storage-class",
            action="store",
            type=str,
            default="STANDARD",
            help="the S3 storage class for created objects",
        )
        rclone_sub = rclone.add_subparsers(help="rclone operations")

        rclone_sync = rclone_sub.add_parser("sync", help="rclone sync")
        rclone_sync.set_defaults(func=self.rclone_sync)
        rclone_sync.add_argument(
            "source",
            action="store",
            type=str,
            help="the source directory for the rclone sync",
        )
        rclone_sync.add_argument(
            "destination",
            action="store",
            type=str,
            help="the destination directory for the rclone sync",
        )

    def argparser_restic(self, a: _SubParsersAction) -> None:
        """
        Configures the restic arguments for the argument parser.
        """
        restic = a.add_parser("restic", help="restic operations")
        restic.add_argument(
            "--repository",
            action="store",
            type=str,
            required=True,
            help="restic repository to operate on",
        )
        restic.add_argument(
            "--cache-dir",
            action="store",
            type=Path,
            required=True,
            help="path to the restic cache directory",
        )
        restic.add_argument(
            "--password-file",
            action="store",
            type=Path,
            required=True,
            help="path to the restic repository's password file",
        )
        restic_sub = restic.add_subparsers(help="restic operations")

        restic_backup = restic_sub.add_parser("backup", help="restic backup")
        restic_backup.add_argument("source", help="source directory for restic backup")
        restic_backup.set_defaults(func=self.restic_backup)

        restic_check = restic_sub.add_parser("check", help="restic check")
        restic_check.set_defaults(func=self.restic_check)

        restic_compare_latest_snapshots = restic_sub.add_parser(
            "compare-latest-snapshots",
            help="compare the latest restic snapshots across copies of a repository",
        )
        restic_compare_latest_snapshots.add_argument(
            "remote_repository", help="remote repository to compare against"
        )
        restic_compare_latest_snapshots.set_defaults(
            func=self.restic_compare_latest_snapshots
        )

        self.argparser_restic_prune_repack(restic_sub)

    def argparser_restic_prune_repack(self, a: _SubParsersAction) -> None:
        """
        Configures the restic arguments for the argument prune-repack action.
        """
        pr = a.add_parser(
            "prune-repack",
            help="prune snapshots and repack data objects in the repository",
        )
        pr.add_argument(
            "--keep-last",
            type=int,
            default=None,
            help="keep this many of the most recent snapshots",
        )
        pr.add_argument(
            "--keep-within-hourly",
            type=str,
            default=None,
            help="keep hourly snapshots taken within this duration",
        )
        pr.add_argument(
            "--keep-within-daily",
            type=str,
            default=None,
            help="keep daily snapshots taken within this duration",
        )
        pr.add_argument(
            "--keep-within-weekly",
            type=str,
            default=None,
            help="keep weekly snapshots taken within this duration",
        )
        pr.add_argument(
            "--keep-within-monthly",
            type=str,
            default=None,
            help="keep monthly snapshots taken within this duration",
        )
        pr.add_argument(
            "--keep-within-yearly",
            type=str,
            default=None,
            help="keep yearly snapshots taken within this duration",
        )

        pr.set_defaults(func=self.restic_prune_repack)

    def configure_logger(self) -> None:
        """
        Configures the logger for this application.
        """
        log = logger(None)
        log.addHandler(StreamHandler(stream=stderr))
        log.setLevel(INFO)

    def rclone_service(self, args: Namespace) -> RcloneService:
        """
        Returns an RcloneService configured according to provided arguments.
        """
        client = RcloneClient(cmdexec)
        client.sync_args = [
            "--bwlimit",
            args.bwlimit,
            "--checksum",
            "--delete-after",
        ]

        client.provider_args = [
            "--s3-provider",
            "AWS",
            "--s3-env-auth",
            "--s3-acl",
            "private",
            "--s3-storage-class",
            args.s3_storage_class,
        ]

        return RcloneService(client)

    def rclone_sync(self, args: Namespace) -> BackupReport:
        """
        Backup operation for rclone sync.
        """
        rclone_service = self.rclone_service(args)
        return rclone_service.sync(
            name=args.name, source=args.source, destination=args.destination
        )

    def restic_service(
        self,
        args: Namespace,
    ) -> ResticService:
        """
        Returns a ResticService configured according to provided arguments.
        """
        client = ResticClient(
            cmdexec, args.repository, args.password_file, args.cache_dir
        )
        return ResticService(client)

    def restic_backup(self, args: Namespace) -> BackupReport:
        """
        Backup operation for restic backup.
        """
        restic_service = self.restic_service(args)
        return restic_service.backup(
            name=args.name,
            source=Path(args.source),
            for_each=True,
            skip_if_unchanged=True,
            exclude_files=[],
        )

    def restic_check(self, args: Namespace) -> BackupReport:
        """
        Backup operation for restic check.
        """
        restic_service = self.restic_service(args)
        return restic_service.check()

    def restic_compare_latest_snapshots(self, args: Namespace) -> BackupReport:
        """
        Snapshot comparison operation for restic.
        """
        restic_service = self.restic_service(args)
        remote_client = ResticClient(
            cmdexec, args.remote_repository, args.password_file, None
        )

        return restic_service.compare_latest_snapshots(remote_client)

    def restic_prune_repack(self, args: Namespace) -> BackupReport:
        """
        Prune and repack operation for restic.

        Prunes old snapshots in accordance with the defined retention policy
        and repacks objects.
        """
        restic_service = self.restic_service(args)

        return restic_service.prune_repack(
            name=args.name,
            keep_last=args.keep_last,
            keep_within_hourly=args.keep_within_hourly,
            keep_within_daily=args.keep_within_daily,
            keep_within_weekly=args.keep_within_weekly,
            keep_within_monthly=args.keep_within_monthly,
            keep_within_yearly=args.keep_within_yearly,
        )

    def reporter(self, args: Namespace) -> BackupReporter:
        """
        Returns a BackupReporter configured according to the provided arguments.
        """
        match args.reporter:
            case "googlechat":
                webhook_url = environ.get("GOOGLE_CHAT_WEBHOOK_URL", None)
                if webhook_url is None:
                    raise ValueError(
                        "missing required environment variable GOOGLE_CHAT_WEBHOOK_URL"
                    )
                return GoogleChatBackupReporter(
                    webhook_url.strip(), GoogleChatReportRenderer(), Session()
                )

            case _:  # pragma: nocover
                # This code should not be reachable; the argument parser should raise
                # an error before we get here.
                raise ValueError(f"invalid reporter type: {args.reporter}")

    def main(self, argv: list[str]) -> int:
        """
        The entrypoint for the backup application.
        """
        self.configure_logger()
        argparser = self.argparser()
        args = argparser.parse_args(argv)
        reporter = self.reporter(args)
        backup_report: BackupReport = args.func(args)
        self.backup_report = backup_report
        reporter.report(backup_report)

        if backup_report.successful:
            return self.RC_OK
        else:
            return self.RC_BACKUP_ERROR
