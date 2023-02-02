"""
lib/build
---------

This module contains common pyinfra build-time code.
"""

from typing import List

from pyinfra import host
from pyinfra.operations import apt, pacman

from .data import load_yaml_data
from .facts import DistroId


def install_system_usability_packages():
    """
    Installs system usability packages.
    """
    install_package_set("usability-packages.yml")


def install_package_set(data_path: str):
    """
    Installs the given package set.
    """
    name = "install system usability packages"
    usability_packages = parse_package_set(data_path)

    distro_id = host.get_fact(DistroId)
    if distro_id == "Debian":
        apt.packages(name=name, packages=usability_packages, present=True, update=True, _sudo=True)  # pyright: ignore
    elif distro_id == "Arch":
        pacman.packages(name=name, packages=usability_packages, present=True, update=True, _sudo=True)  # pyright: ignore
    else:
        raise Exception(f"don't know how to install packages for distribution {distro_id}")


def parse_package_set(data_path: str) -> List[str]:
    """
    Parses a package set structured roughly like:

        $common_package_name:
            $linux_distribution_name: $package_name

    Or, alternatively:

        $common_package_name:
            $linux_distribution_name:
                - $package_1
                - $package_2

    Returns a list of all packages to be installed on the host Linux distribution.
    """
    raw = load_yaml_data(data_path)

    distro_name = host.get_fact(DistroId) # pyright: ignore
    pkgs_to_install = list()
    for pkg_name, pkg in raw.items():
        distro_pkgs = pkg[distro_name]
        if isinstance(distro_pkgs, list):
            pass
        elif isinstance(distro_pkgs, str):
            distro_pkgs = [distro_pkgs]
        else:
            raise Exception(f"failed parsing package {pkg_name} from data {data_path}")
        pkgs_to_install.extend(distro_pkgs)
    return pkgs_to_install
