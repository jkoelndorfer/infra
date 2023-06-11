"""
lib/data
--------

This module contains code for working with data stored in the
data/ directory under the root of pyinfra.
"""

from os import path
import re
from typing import Mapping

import yaml

from .model.packages import PackageSet


_ssm_client = None
_pyinfra_root = path.abspath(path.join(path.dirname(__file__), ".."))
_pyinfra_data_root = path.join(_pyinfra_root, "data")


def load_data(data_path: str, strip_comments: bool) -> str:
    """
    Loads data from a file in $PYINFRA_ROOT/data and returns it
    as a string.
    """
    comment_re = re.compile(r"^\s*#")
    with open(path.join(_pyinfra_data_root, data_path), "r") as f:
        return "\n".join(l for l in f.readlines() if not strip_comments or not comment_re.match(l))


def load_package_set(package_set_name: str) -> PackageSet:
    """
    Parses a package set structured roughly like:

        $common_package_name:
            $linux_distribution_name: $package_name

    Or, alternatively:

        $common_package_name:
            $linux_distribution_name:
                - $package_1
                - $package_2

    Returns a PackageSet object.
    """
    try:
        raw = load_yaml_data(path.join(_pyinfra_data_root, "global", "package-sets", f"{package_set_name}.yml"))
    except Exception as e:
        raise Exception(f"failed to load package set {package_set_name}") from e

    pkg_set = PackageSet()
    for common_pkg_name, pkgs_by_distro in raw.items():
        for distro_name, pkgs in pkgs_by_distro.items():
            if distro_name == "Debian":
                m = pkg_set.add_debian_package
            elif distro_name == "Arch":
                m = pkg_set.add_arch_package
            else:
                raise Exception(f"unrecognized distro: {distro_name}")

            # A distribution's package value can be one of three things:
            #
            # 1. A list of strings. This allows for one common package name
            #    to install multiple packages. Sometimes, distributions split
            #    one logical piece of software into a few different packages
            #    since certain components are optional.
            #
            # 2. A string, to install a single package.
            #
            # 3. None, to indicate that the package is a "no-op" on that
            #    distribution.
            errmsg = f"invalid package definition for {common_pkg_name}/{distro_name}"
            if isinstance(pkgs, list):
                for p in pkgs:
                    if not isinstance(p, str):
                        raise Exception(errmsg)
                    m(p)
            elif isinstance(pkgs, str):
                m(pkgs)
            elif pkgs is None:
                pass
            else:
                raise Exception(errmsg)

    return pkg_set


def load_yaml_data(data_path: str) -> Mapping:
    """
    Loads data from a file in $PYINFRA_ROOT/data, parses it as
    YAML, and returns the resulting object.
    """
    return yaml.safe_load(load_data(data_path, strip_comments=False))
