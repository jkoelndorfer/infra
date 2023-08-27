"""
lib/build/docker
----------------

This module contains build-time docker code.
"""

from shlex import quote as sv

from .common import install_package_set
from ..model.container import Container
from ..pyinfra import Pyinfra


def install_docker(pyinfra: Pyinfra):
    """
    Installs docker.
    """
    p = pyinfra.ctx("docker")
    install_package_set(p, "docker")


def docker_pull(pyinfra: Pyinfra, ctr: Container) -> None:
    """
    Pulls the image of the container described by `ctr`.
    """
    p = pyinfra.ctx("docker")
    p.server.shell(
        name=f"pull image: {ctr.image}",
        commands=[f"docker pull {sv(ctr.image)}"],
    )
