"""
roles/miniserv/build
--------------------

This module contains build logic for the miniserv role.
"""

from os import path

from pyinfra.operations import apt, files

from lib import vars as gvars
from lib.aws import aws_access_key_id, aws_secret_access_key
from lib.build.common import build_common, install_package_set
from lib.build.docker import install_docker
from lib.operations import aws

from . import vars


def build():
    build_common()
    install_package_set("aws-cli")
    install_aqgo()
    install_docker()
    install_rclone()


def install_aqgo():
    aws.s3_download(
        name="[aqgo] download aqgo binary",
        src=vars.aqgo_s3_uri,
        dest="/usr/local/bin/aqgo",
        user="root",
        group="root",
        mode="0555",
        sha256sum=vars.aqgo_sha256sum,
        aws_access_key_id=aws_access_key_id(),
        aws_secret_access_key=aws_secret_access_key(),
        _sudo=True,
    )


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
