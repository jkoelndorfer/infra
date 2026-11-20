"""
projects.homelab.samba.share
============================

This module describes Samba shares and the accounts that access them, and renders
them into the configuration files that the Samba image reads [1].

Every share is backed by its own volume, and every account is a Unix account in the
container, created by the image from users.conf at startup.

[1]: https://github.com/dockur/samba/blob/v4.23.10-r0/samba.sh
"""

from dataclasses import dataclass
from pathlib import PurePosixPath

from pulumi import Output

from ..kubernetes import HomelabContainerVolumeProvisionedSource


@dataclass(frozen=True)
class SambaAccount:
    """
    An account that authenticates to Samba.
    """

    name: str
    uid: int
    password: Output[str]


@dataclass(frozen=True)
class SambaShare:
    """
    A share, the volume backing it, and the accounts permitted to use it.
    """

    name: str
    comment: str
    accounts: list[SambaAccount]

    owner: SambaAccount
    """
    The account that every file operation on the share runs as, whichever account
    authenticated. The share's volume is owned by this account's UID.
    """

    volume: HomelabContainerVolumeProvisionedSource

    def __post_init__(self) -> None:
        if self.owner not in self.accounts:
            raise ValueError(
                f"share {self.name!r}: owner {self.owner.name!r} must be one of "
                "its accounts"
            )

    @property
    def path(self) -> PurePosixPath:
        """
        Where the share's volume is mounted in the container.
        """
        return PurePosixPath("/shares") / self.name

    def smb_conf_section(self, group: str) -> str:
        """
        Returns the share's section of smb.conf. Files are created as the owner and
        the given group, and are readable only through the share.
        """
        valid_users = " ".join(a.name for a in self.accounts)
        return "\n".join(
            [
                f"[{self.name}]",
                f"comment = {self.comment}",
                f"path = {self.path}",
                f"valid users = {valid_users}",
                "read only = no",
                "browseable = yes",
                f"force user = {self.owner.name}",
                f"force group = {group}",
                "create mask = 0600",
                "directory mask = 0700",
            ]
        )


def smb_conf(shares: list[SambaShare], group: str) -> str:
    """
    Returns smb.conf for a standalone server that serves the given shares over SMB2
    or later, on port 445 only, to authenticated accounts only.
    """
    global_section = "\n".join(
        [
            "[global]",
            "server role = standalone server",
            "security = user",
            "map to guest = never",
            "server min protocol = SMB2",
            "smb ports = 445",
            "disable netbios = yes",
            "load printers = no",
            "printing = bsd",
            "printcap name = /dev/null",
            "disable spoolss = yes",
        ]
    )
    sections = [global_section, *(s.smb_conf_section(group) for s in shares)]
    return "\n\n".join(sections) + "\n"


def users_conf(accounts: list[SambaAccount], group: str, gid: int) -> Output[str]:
    """
    Returns users.conf, in which each line is
    `username:uid:groupname:gid:password:homedir`. Every account's primary group is
    the given group. The home directory is left empty, so the image uses its
    default, which no share exposes.
    """
    for a in accounts:
        if ":" in a.name:
            raise ValueError(f"account name {a.name!r} must not contain ':'")

    def render(passwords: list[str]) -> str:
        lines = []
        for account, password in zip(accounts, passwords, strict=True):
            # The image splits each line on ':', and skips lines with too many
            # fields instead of failing.
            if ":" in password or "\n" in password:
                raise ValueError(
                    f"the password of {account.name!r} contains ':' or a newline"
                )
            lines.append(f"{account.name}:{account.uid}:{group}:{gid}:{password}:")
        return "\n".join(lines) + "\n"

    return Output.all(*(a.password for a in accounts)).apply(render)
