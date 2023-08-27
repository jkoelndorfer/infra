"""
roles/miniserv/build
--------------------

This module contains build logic for the miniserv role.
"""

from os import path

from lib import vars as gvars
from lib.aws import aws_access_key_id, aws_secret_access_key
from lib.build.common import build_common, install_package_set
from lib.build.docker import install_docker, docker_pull
from lib.pyinfra import Pyinfra

from .containers import service_containers
from . import vars


def build(p: Pyinfra):
    build_common(p)
    install_package_set(p, "aws-cli")
    install_aqgo(p)
    install_docker(p)
    install_rclone(p)
    pull_service_container_images(p)


def install_aqgo(pyinfra: Pyinfra):
    p = pyinfra.ctx("aqgo")
    p.aws.s3_download(
        name="download aqgo binary",
        src=vars.aqgo_s3_uri,
        dest="/usr/local/bin/aqgo",
        user="root",
        group="root",
        mode="0555",
        sha256sum=vars.aqgo_sha256sum,
        aws_access_key_id=aws_access_key_id(),
        aws_secret_access_key=aws_secret_access_key(),
    )


def install_rclone(pyinfra: Pyinfra):
    rclone_deb_path = path.join(gvars.build_cache_dir, "rclone.deb")
    p = pyinfra.ctx("rclone")
    p.files.download(
        name="download package",
        src=vars.rclone_deb_url,
        dest=rclone_deb_path,
        user="root",
        group="root",
        mode="0444",
        sha256sum=vars.rclone_deb_sha256sum,
    )

    p.apt.deb(
        name="install package",
        src=rclone_deb_path,
    )


def pull_service_container_images(pyinfra: Pyinfra):
    for c in service_containers:
        docker_pull(pyinfra, c)
