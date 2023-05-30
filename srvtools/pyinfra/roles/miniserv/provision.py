"""
roles/miniserv/build
--------------------

This module contains provision logic for the miniserv role.
"""

from os import path
from shlex import quote

from lib.aws import aws_access_key_id, aws_secret_access_key, ssm_parameter_value
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
    provision_aqgo()
    provision_container_networks()
    provision_service_containers()
    provision_rclone_backup()
    provision_vaultwarden_backup()


def provision_aqgo():
    aqgo_files_dir = path.join(vars.files_dir, "aqgo")

    aqgo_env = files.template(
        name="[aqgo] aqgo env",
        src=path.join(aqgo_files_dir, "aqgo.conf.j2"),
        dest="/etc/aqgo.conf",
        user="root",
        group="root",
        mode="0400",
        _sudo=True,
        quote=quote,
        aws_default_region=gvars.aws_default_region,
        aws_access_key_id=ssm_parameter_value("/prod/air_quality/aws_iam_access_key_id"),
        aws_secret_access_key=ssm_parameter_value("/prod/air_quality/aws_iam_secret_access_key"),
    )  # pyright: ignore

    aqgo_systemd_unit = files.template(
        name="[aqgo] aqgo service systemd unit",
        src=path.join(aqgo_files_dir, "aqgo.service.j2"),
        dest=path.join(gvars.systemd_unit_dir, "aqgo.service"),
        user="root",
        group="root",
        mode="0444",
        _sudo=True,
        serial_device_path=vars.aqgo_serial_device_path,
        metric_namespace=vars.aqgo_metric_namespace,
    )  # pyright: ignore

    systemd.service(
        name="[aqgo] start aqgo",
        service="backup.timer",
        running=True,
        restarted=aqgo_env.changed or aqgo_systemd_unit.changed,
        enabled=True,
        daemon_reload=aqgo_systemd_unit.changed,
        _sudo=True,
    )  # pyright: ignore


def provision_container_networks():
    for network in swag_networks():
        docker_network(network)


def provision_rclone_backup():
    backup_files_dir = path.join(vars.files_dir, "backup")
    backup_config_dir = "/etc/backup"

    files.put(
        name="[rclone] install backup script",
        src=path.join(backup_files_dir, "backup"),
        dest="/usr/local/bin/backup",
        user="root",
        group="root",
        mode="0555",
        _sudo=True,
    )

    files.directory(
        name="[rclone] backup config directory",
        path=backup_config_dir,
        user="root",
        group="root",
        mode="0555",
        _sudo=True,
    )

    files.template(
        name="[rclone] backup env",
        src=path.join(backup_files_dir, "env.conf.j2"),
        dest=path.join(backup_config_dir, "env.conf"),
        user="root",
        group="root",
        mode="0400",
        _sudo=True,
        quote=quote,
        aws_default_region=gvars.aws_default_region,
        aws_access_key_id=aws_access_key_id(),
        aws_secret_access_key=aws_secret_access_key(),
    )  # pyright: ignore

    files.template(
        name="[rclone] syncthing config",
        src=path.join(backup_files_dir, "syncthing.conf.j2"),
        dest=path.join(backup_config_dir, "syncthing.conf"),
        user="root",
        group="root",
        mode="0444",
        _sudo=True,
        quote=quote,
        backup_working_dir=container_data_dir(syncthing_container.name),
        backup_src=vars.syncthing_backup_src,
        backup_dest=ssm_parameter_value("/prod/backup/rclone_dest"),
        bw_limit=vars.syncthing_bw_limit,
    )  # pyright: ignore

    backup_service = files.put(
        name="[rclone] backup service systemd unit",
        src=path.join(backup_files_dir, "backup.service"),
        dest=path.join(gvars.systemd_unit_dir, "backup.service"),
        user="root",
        group="root",
        mode="0444",
        _sudo=True,
    )

    backup_timer = files.template(
        name="[rclone] backup timer systemd unit",
        src=path.join(backup_files_dir, "backup.timer.j2"),
        dest=path.join(gvars.systemd_unit_dir, "backup.timer"),
        user="root",
        group="root",
        mode="0444",
        backup_time=vars.syncthing_backup_time,
        _sudo=True,
    )  # pyright: ignore

    systemd.service(
        name="[rclone] start backup timer",
        service="backup.timer",
        running=True,
        enabled=True,
        restarted=backup_timer.changed,
        daemon_reload=backup_service.changed or backup_timer.changed,
        _sudo=True,
    )  # pyright: ignore


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
        enabled=True,
        restarted=backup_timer.changed,
        daemon_reload=backup_service.changed or backup_timer.changed,
        _sudo=True,
    )  # pyright: ignore
