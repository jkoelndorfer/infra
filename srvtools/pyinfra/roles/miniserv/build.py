"""
roles/miniserv/build
--------------------

This module contains build logic for the miniserv role.
"""

from lib.build.common import build_common
from lib.build.docker import install_docker


def build():
    build_common()
    install_docker()
