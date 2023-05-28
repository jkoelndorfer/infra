"""
roles/miniserv/build
--------------------

This module contains provision logic for the miniserv role.
"""

from os import path
from shlex import quote

from lib.provision.docker import docker_ctr, docker_network
from lib import vars as gvars
from pyinfra.operations import files, systemd

from .containers import service_containers, syncthing_container, vaultwarden_container
from .containerlib import container_data_dir, swag_networks
from . import vars


def syncthing_data_volume_dir() -> str:
    """
    Returns the path to Syncthing's data volume, which is a subdirectory of the
    container's entire data directory.

    That is, this function will return:

    /srv/data/0/syncthing/data

    and not:

    /srv/data/0/syncthing
    """
    return [v.src for v in syncthing_container.volumes if path.basename(v.src) == "data"][0]


def vaultwarden_data_volume_dir() -> str:
    """
    Returns the path to Vaultwarden's data volume, which is a subdirectory of the
    container's entire data directory.

    That is, this function will return:

    /srv/data/0/vaultwarden/data

    and not:

    /srv/data/0/vaultwarden
    """
    return [v.src for v in vaultwarden_container.volumes if path.basename(v.src) == "data"][0]


def provision():
    provision_container_networks()
    provision_service_containers()
    provision_vaultwarden_backup()


def provision_container_networks():
    for network in swag_networks():
        docker_network(network)


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
        docker_ctr(ctr)


def provision_vaultwarden_backup():
    vaultwarden_files_dir = path.join(vars.files_dir, "vaultwarden")
    vaultwarden_syncthing_data = path.join(
        syncthing_data_volume_dir(), vaultwarden_container.name
    )
    files.template(
        name="[vaultwarden] configure backup",
        src=path.join(vaultwarden_files_dir, "vaultwarden-backup.conf.j2"),
        dest="/etc/vaultwarden-backup.conf",
        user="root",
        group="root",
        mode="0444",
        quote=quote,
        vaultwarden_container_name=vaultwarden_container.name,
        vaultwarden_data_dir=vaultwarden_data_volume_dir(),
        vaultwarden_syncthing_dir=vaultwarden_syncthing_data,
        _sudo=True,
    )  # pyright: ignore

    backup_service = files.put(
        name="[vaultwarden] configure backup service",
        src=path.join(vaultwarden_files_dir, "vaultwarden-backup.service"),
        dest=path.join(gvars.systemd_unit_dir, "vaultwarden-backup.service"),
        user="root",
        group="root",
        mode="0444",
        _sudo=True,
    )  # pyright: ignore

    backup_timer = files.template(
        name="[vaultwarden] configure backup timer",
        src=path.join(vaultwarden_files_dir, "vaultwarden-backup.timer.j2"),
        dest=path.join(gvars.systemd_unit_dir, "vaultwarden-backup.timer"),
        user="root",
        group="root",
        mode="0444",
        backup_time=vars.vaultwarden_backup_time,
        _sudo=True,
    )  # pyright: ignore

    systemd.service(
        name="[vaultwarden] start backup timer",
        service="vaultwarden-backup.timer",
        running=True,
        restarted=backup_timer.changed,
        daemon_reload=backup_service.changed or backup_timer.changed,
        _sudo=True,
    )  # pyright: ignore
