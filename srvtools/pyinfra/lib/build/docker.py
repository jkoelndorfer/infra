"""
lib/build/docker
----------------

This module contains build-time docker code.
"""

from .common import install_package_set


def install_docker():
    """
    Installs docker.
    """
    install_package_set("docker")
