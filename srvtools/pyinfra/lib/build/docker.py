"""
lib/build/docker
----------------

This module contains build-time docker code.
"""

from .common import install_package_set
from ..pyinfra import Pyinfra


def install_docker(pyinfra: Pyinfra):
    """
    Installs docker.
    """
    p = pyinfra.ctx("docker")
    install_package_set(p, "docker")
