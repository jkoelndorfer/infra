"""
lib/build/podman
----------------

This module contains build-time podman code.
"""

from shlex import quote as shell_quote
from typing import List

from pyinfra.operations import server

from ..model.container import Container
from .packages import install_package_set


def install_podman():
    return install_package_set("podman")


def pull_ctr_images(ctrs: List[Container]):
    for c in ctrs:
        ctr_image_quoted = shell_quote(c.image)
        server.shell(
            name=f"podman container image pull: {c.name}",
            commands=[f"podman pull {ctr_image_quoted}"]
        ) # pyright: ignore


def setup_podman(ctrs: List[Container]):
    """
    Performs all podman build-time setup.
    """
    install_podman()
    pull_ctr_images(ctrs)
