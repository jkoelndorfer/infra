"""
roles/edgerouter/build
----------------------

This module contains build logic for the edgerouter role.
"""

from pyinfra.operations import files

from . import vars


def build():
    files.directory(
        path=vars.wireguard_cache_dir,
        user="root",
        group="root",
        mode="0755",
    )
    files.download(
        src=vars.wireguard_deb_url,
        dest=f"{vars.wireguard_cache_dir}/wireguard.deb",
        user="root",
        group="root",
        mode="0444",
        sha256sum=vars.wireguard_deb_sha256sum,
    )
