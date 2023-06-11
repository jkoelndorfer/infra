"""
lib/model/packages
------------------

This module contains package-related object models.
"""

from typing import List


# This PackageSet could have just been a map from DistroId -> list,
# but this implementation provides nice autocompletion.
class PackageSet:
    """
    Represents a set of packages that can be installed on a system.
    """

    def __init__(self) -> None:
        self.debian_packages: List[str] = list()
        self.arch_packages: List[str] = list()

    def add_debian_package(self, package_name: str) -> None:
        """
        Adds a Debian package to this package set.

        `package_name` should be the name of the package as
        defined in Debian repositories.
        """
        self.debian_packages.append(package_name)

    def add_arch_package(self, package_name: str) -> None:
        """
        Adds an Arch Linux package to this package set.

        `package_name` should be the name of the package as
        defined in Arch repositories.
        """
        self.arch_packages.append(package_name)
