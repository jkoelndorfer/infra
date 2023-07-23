"""
lib/build/packages
------------------

This module contains build-time package management code.
"""

from lib.pyinfra import Pyinfra
from ..data import load_package_set
from ..error import UnsupportedLinuxDistribution
from ..vars import distro_id


def install_package_set(pyinfra: Pyinfra, name: str):
    """
    Installs the given package set.
    """
    op_name = f"install package set {name}"
    package_set = load_package_set(name)

    with pyinfra.ctx("package") as p:
        if distro_id == "Debian":
            p.apt.packages(
                name=op_name,
                packages=package_set.debian_packages,
                present=True,
                update=True,
            )
        elif distro_id == "Arch":
            p.pacman.packages(
                name=op_name,
                packages=package_set.arch_packages,
                present=True,
                update=True,
            )
        else:
            raise UnsupportedLinuxDistribution(distro_id)
