"""
roles/miniserv/build
--------------------

This module contains build logic for the miniserv role.
"""

from pyinfra.operations import apt, server

from lib.build.common import build_common
from lib.build.podman import setup_podman
from . import vars


def build():
    build_common()
    setup_podman(ctrs=vars.containers)
