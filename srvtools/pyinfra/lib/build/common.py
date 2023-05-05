"""
lib/build/common
----------------

This module contains common build-time tasks.

Most hosts configured by pyinfra should run these tasks at build time.
"""

from .packages import install_package_set


def build_common():
    install_package_set("usability-packages")


def configure_pyinfra_staging_dir():
    """
    Configures a directory that is used by pyinfra to stage files.

    The files in this staging directory should only be used during
    the pyinfra provisioning process.
    """
