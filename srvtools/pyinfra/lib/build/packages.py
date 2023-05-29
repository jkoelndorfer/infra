"""
lib/build/packages
------------------

This module contains build-time package management code.
"""

from pyinfra.operations import apt, pacman

from ..data import load_package_set
from ..error import UnsupportedLinuxDistribution
from ..vars import distro_id


def install_package_set(name: str):
    """
    Installs the given package set.
    """
    op_name = f"[packages] install package set {name}"
    package_set = load_package_set(name)

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
        raise UnsupportedLinuxDistribution(distro_id)
