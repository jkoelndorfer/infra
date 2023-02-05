"""
lib/build/common
----------------

This module contains common build-time tasks.

Most hosts configured by pyinfra should run these tasks at build time.
"""

from .packages import install_package_set


def build_common():
    install_package_set("usability-packages")
