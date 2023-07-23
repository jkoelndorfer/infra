"""
lib/build/common
----------------

This module contains common build-time tasks.

Most hosts configured by pyinfra should run these tasks at build time.
"""

from lib import vars
from lib.pyinfra import Pyinfra
from .packages import install_package_set


def build_common(pyinfra: Pyinfra):
    with pyinfra.ctx("common") as p:
        p.files.directory(
            name="create build cache directory",
            path=vars.build_cache_dir,
            user="root",
            group="root",
            mode="0755",
        )
        install_package_set(p, "usability-packages")
