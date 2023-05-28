"""
lib/build/common
----------------

This module contains common build-time tasks.

Most hosts configured by pyinfra should run these tasks at build time.
"""

from pyinfra.operations import files

from lib import vars
from .packages import install_package_set


def build_common():
    files.directory(
        name="[common] create build cache directory",
        path=vars.build_cache_dir,
        user="root",
        group="root",
        mode="0755",
    )
    install_package_set("usability-packages")
