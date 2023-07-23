"""
roles/edgerouter/build
----------------------

This module contains build logic for the edgerouter role.
"""

from lib.pyinfra import Pyinfra
from . import vars

p = Pyinfra(["edgerouter"])


def build(pyinfra: Pyinfra):
    p = pyinfra.ctx("wireguard")
    p.files.directory(
        name="configure wireguard cache directory",
        path=vars.wireguard_cache_dir,
        user="root",
        group="root",
        mode="0755",
    )
    p.files.download(
        name="download wireguard package",
        src=vars.wireguard_deb_url,
        dest=f"{vars.wireguard_cache_dir}/wireguard.deb",
        user="root",
        group="root",
        mode="0444",
        sha256sum=vars.wireguard_deb_sha256sum,
    )
