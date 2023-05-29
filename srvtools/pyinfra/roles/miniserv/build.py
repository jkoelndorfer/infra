"""
roles/miniserv/build
--------------------

This module contains build logic for the miniserv role.
"""

from os import path

from pyinfra.operations import apt, files

from lib import vars as gvars
from lib.build.common import build_common
from lib.build.docker import install_docker

from . import vars


def build():
    build_common()
    install_docker()
    install_rclone()


def install_rclone():
    rclone_deb_path = path.join(gvars.build_cache_dir, "rclone.deb")
    files.download(
        name="[rclone] download package",
        src=vars.rclone_deb_url,
        dest=rclone_deb_path,
        user="root",
        group="root",
        mode="0444",
        sha256sum=vars.rclone_deb_sha256sum,
        _sudo=True,
    )

    apt.deb(
        name="[rclone] install package",
        src=rclone_deb_path,
        _sudo=True,
    )  # pyright: ignore
