"""
projects.homelab.samba.scans
============================

This module provisions the share that the printer saves walk-up scans to, using its
Scan to Network Folder feature.

Two accounts use it, rather than one per person:

- `scanner` is only for the printer, which stores its credential.
- `scanuser` is for the people who collect the scans.

Either can be rotated without affecting the other. Files are owned by `scanner`
whichever account wrote them, so both can read and delete everything in the share.

Scans are transient, so the share is deliberately left out of backups.

NOTE: The printer must speak SMB2 or later, because the server rejects SMB1. Older
printer firmware only supports SMB1; update it if the printer's test of the network
folder fails to connect.

NOTE: To read an account's password:

    $ kubectl -n $NAMESPACE get secret samba-accounts \\
        -o jsonpath='{.data.scanner}' | base64 -d
"""

from pulumi import ResourceOptions
import pulumi_random as random

from infralib import DeploymentContext

from ..kubernetes import HomelabContainerVolumeProvisionedSource, uid_gid
from .share import SambaAccount, SambaShare


def provision_scan_share(dctx: DeploymentContext, service_name: str) -> SambaShare:
    """
    Provisions the accounts for the share that receives document scans, and returns
    the share.
    """
    env = dctx.target.environment
    random_opts = ResourceOptions(provider=dctx.provider_factory.random_provider())

    def account(name: str, uid: int) -> SambaAccount:
        # Someone types the printer's password into its web interface, so it
        # avoids special characters.
        password = random.RandomPassword(
            f"{name}_password",
            length=32,
            lower=True,
            upper=True,
            numeric=True,
            special=False,
            opts=random_opts,
        )
        return SambaAccount(name=name, uid=uid, password=password.result)

    # The printer's account owns the volume, so it shares the service's UID.
    scanner = account("scanner", uid_gid(env, service_name))
    scanuser = account("scanuser", uid_gid(env, f"{service_name}-scanuser"))

    return SambaShare(
        name="scans",
        comment="Document scans",
        accounts=[scanner, scanuser],
        owner=scanner,
        volume=HomelabContainerVolumeProvisionedSource(
            backing_volume="data0",
            storage="20Gi",
            access_modes=["ReadWriteOnce"],
            mode="0700",
        ),
    )
