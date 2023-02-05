"""
lib/build/packages
------------------

This module contains build-time package management code.
"""

from typing import List

from pyinfra import host
from pyinfra.operations import apt, pacman

from ..data import load_package_set
from ..facts import DistroId


def install_package_set(name: str):
    """
    Installs the given package set.
    """
    op_name = f"install package set {name}"
    package_set = load_package_set(name)

    distro_id = host.get_fact(DistroId)
    if distro_id == "Debian":
        apt.packages(
            name=op_name,
            packages=package_set.debian_packages,
            present=True,
            update=True,
            _sudo=True
        )  # pyright: ignore
    elif distro_id == "Arch":
        pacman.packages(
            name=op_name,
            packages=package_set.arch_packages,
            present=True,
            update=True,
            _sudo=True
        )  # pyright: ignore
    else:
        raise Exception(f"don't know how to install packages for distribution {distro_id}")
