"""
roles/miniserv/build
--------------------

This module contains provision logic for the miniserv role.
"""

from os import path

from lib.provision.podman import podman_ctr

from .containers import service_containers
from .containerlib import container_data_dir


def provision():
    provision_service_containers()


def provision_service_containers():
    for ctr in service_containers:
        for v in ctr.volumes:
            # For container volumes that are "relative", automatically
            # ensure they are placed under that container's designated
            # data directory.
            #
            # This is only implied for miniserv because Docker (and by
            # extension, probably Podman), allow for named volumes
            # when the source is not a path.
            #
            # In miniserv's case, we always want our container data
            # to live in a known location on the filesystem.
            if not path.isabs(v.src):
                v.src = path.join(container_data_dir(ctr.name), v.src)
        podman_ctr(ctr)
