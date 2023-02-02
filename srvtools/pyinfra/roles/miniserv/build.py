"""
roles/miniserv/build
--------------------

This module contains build logic for the miniserv role.
"""

from pyinfra.operations import apt, server

from lib.build import install_system_usability_packages
from . import vars


def build():
    install_system_usability_packages()
    install_miniserv_packages()
    pull_container_images()


def install_miniserv_packages():
    apt.packages(name="install podman", packages=["podman"], _sudo=True)  # pyright: ignore


def pull_container_images():
    server.shell(
        name="pull container images",
        commands=[
            f"podman pull docker.io/{c}"
            for c in vars.container_images
        ],
        _sudo=True,
    )
