"""
roles/miniserv/build
--------------------

This module contains provision logic for the miniserv role.
"""

from os import path
from shlex import quote
from typing import List

from lib.aws import aws_access_key_id, aws_secret_access_key, ssm_parameter_value
from lib.provision.docker import docker_ctr, docker_network
from lib import vars as gvars

from lib.pyinfra import Pyinfra
from .containers import service_containers, swag_container, syncthing_container, vaultwarden_container
from .containerlib import container_data_dir, swag_networks
from . import vars


def swag_config_volume_dir() -> str:
    """
    Returns the path to SWAG's data volume, which is a subdirectory of the
    container's entire data directory.

    That is, this function will return:

    /srv/data/0/swag/config

    and not:

    /srv/data/0/swag
    """
    return [v.src for v in swag_container.volumes if path.basename(v.src) == "config"][0]


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


def provision(p: Pyinfra):
    force_restart_containers = []

    correct_ctr_source_paths()
    provision_aqgo(p)
    provision_container_networks(p)
    swag_config_changed = provision_swag_config(p)
    if swag_config_changed:
        force_restart_containers.append("swag")
    provision_service_containers(p, force_restart_containers)
    provision_rclone_backup(p)
    provision_vaultwarden_backup(p)


def correct_ctr_source_paths():
    """
    For container volumes that are "relative", automatically
    ensure they are placed under that container's designated
    data directory.

    This is only implied for miniserv because Docker (and by
    extension, probably Podman), allow for named volumes
    when the source is not a path.

    In miniserv's case, we always want our container data
    to live in a known location on the filesystem.
    """
    for ctr in service_containers:
        for v in ctr.volumes:
            if not path.isabs(v.src):
                v.src = path.join(container_data_dir(ctr.name), v.src)


def provision_aqgo(pyinfra: Pyinfra):
    aqgo_files_dir = path.join(vars.files_dir, "aqgo")

    with pyinfra.ctx("aqgo") as p:
        aqgo_env = p.files.template(
            name="env",
            src=path.join(aqgo_files_dir, "aqgo.conf.j2"),
            dest="/etc/aqgo.conf",
            user="root",
            group="root",
            mode="0400",
            quote=quote,
            aws_default_region=gvars.aws_default_region,
            aws_access_key_id=ssm_parameter_value("/prod/air_quality/aws_iam_access_key_id"),
            aws_secret_access_key=ssm_parameter_value("/prod/air_quality/aws_iam_secret_access_key"),
        )

        aqgo_systemd_unit = p.files.template(
            name="service systemd unit",
            src=path.join(aqgo_files_dir, "aqgo.service.j2"),
            dest=path.join(gvars.systemd_unit_dir, "aqgo.service"),
            user="root",
            group="root",
            mode="0444",
            serial_device_path=vars.aqgo_serial_device_path,
            metric_namespace=vars.aqgo_metric_namespace,
        )

        p.systemd.service(
            name="start aqgo",
            service="backup.timer",
            running=True,
            restarted=aqgo_env.changed or aqgo_systemd_unit.changed,
            enabled=True,
            daemon_reload=aqgo_systemd_unit.changed,
        )


def provision_container_networks(pyinfra: Pyinfra):
    for network in swag_networks():
        docker_network(pyinfra, network)


def provision_rclone_backup(pyinfra: Pyinfra):
    backup_files_dir = path.join(vars.files_dir, "backup")
    backup_config_dir = "/etc/backup"

    with pyinfra.ctx("rclone") as p:
        p.files.put(
            name="install backup script",
            src=path.join(backup_files_dir, "backup"),
            dest="/usr/local/bin/backup",
            user="root",
            group="root",
            mode="0555",
        )

        p.files.directory(
            name="backup config directory",
            path=backup_config_dir,
            user="root",
            group="root",
            mode="0555",
        )

        p.files.template(
            name="backup env",
            src=path.join(backup_files_dir, "env.conf.j2"),
            dest=path.join(backup_config_dir, "env.conf"),
            user="root",
            group="root",
            mode="0400",
            quote=quote,
            aws_default_region=gvars.aws_default_region,
            aws_access_key_id=aws_access_key_id(),
            aws_secret_access_key=aws_secret_access_key(),
        )

        p.files.template(
            name="syncthing config",
            src=path.join(backup_files_dir, "syncthing.conf.j2"),
            dest=path.join(backup_config_dir, "syncthing.conf"),
            user="root",
            group="root",
            mode="0444",
            quote=quote,
            backup_working_dir=container_data_dir(syncthing_container.name),
            backup_src=vars.syncthing_backup_src,
            backup_dest=ssm_parameter_value("/prod/backup/rclone_dest"),
            bw_limit=vars.syncthing_bw_limit,
        )

        backup_service = p.files.put(
            name="backup service systemd unit",
            src=path.join(backup_files_dir, "backup.service"),
            dest=path.join(gvars.systemd_unit_dir, "backup.service"),
            user="root",
            group="root",
            mode="0444",
        )

        backup_timer = p.files.template(
            name="backup timer systemd unit",
            src=path.join(backup_files_dir, "backup.timer.j2"),
            dest=path.join(gvars.systemd_unit_dir, "backup.timer"),
            user="root",
            group="root",
            mode="0444",
            backup_time=vars.syncthing_backup_time,
        )

        p.systemd.service(
            name="start backup timer",
            service="backup.timer",
            running=True,
            enabled=True,
            restarted=backup_timer.changed,
            daemon_reload=backup_service.changed or backup_timer.changed,
        )


def provision_service_containers(p: Pyinfra, force_restart_containers: List[str]):
    for ctr in service_containers:
        docker_ctr(p, ctr, force_restart=(ctr.name in force_restart_containers))


def provision_swag_config(pyinfra: Pyinfra) -> bool:
    """
    Provisions configuration for the SWAG container.

    Returns `True` if any configuration has changed, `False` otherwise.
    """
    swag_files_dir = path.join(vars.files_dir, "swag")
    p = pyinfra.ctx("swag")

    swag_configs = [
        "pihole",
        "syncthing",
        "unifi-controller",
        "vaultwarden",
    ]
    ops = []
    for c in swag_configs:
        config_filename = f"{c}.subdomain.conf"
        op = p.files.put(
            name=f"deploy swag config: {c}",
            src=path.join(swag_files_dir, config_filename),
            dest=path.join(swag_config_volume_dir(), "nginx", "proxy-confs", config_filename),
            user="root",
            group="root",
            mode="0444",
        )
        ops.append(op)
    return any([o.changed for o in ops])


def provision_vaultwarden_backup(pyinfra: Pyinfra):
    vaultwarden_files_dir = path.join(vars.files_dir, "vaultwarden")
    vaultwarden_syncthing_data = path.join(syncthing_data_volume_dir(), vaultwarden_container.name)

    with pyinfra.ctx("vaultwarden") as p:
        p.files.template(
            name="configure backup",
            src=path.join(vaultwarden_files_dir, "vaultwarden-backup.conf.j2"),
            dest="/etc/vaultwarden-backup.conf",
            user="root",
            group="root",
            mode="0444",
            quote=quote,
            vaultwarden_container_name=vaultwarden_container.name,
            vaultwarden_data_dir=vaultwarden_data_volume_dir(),
            vaultwarden_syncthing_dir=vaultwarden_syncthing_data,
        )

        p.files.put(
            name="deploy backup script",
            src=path.join(vaultwarden_files_dir, "vaultwarden-backup"),
            dest=path.join(gvars.systemd_unit_dir, "vaultwarden-backup"),
            user="root",
            group="root",
            mode="0555",
        )

        backup_service = p.files.put(
            name="configure backup service",
            src=path.join(vaultwarden_files_dir, "vaultwarden-backup.service"),
            dest=path.join(gvars.systemd_unit_dir, "vaultwarden-backup.service"),
            user="root",
            group="root",
            mode="0444",
        )

        backup_timer = p.files.template(
            name="configure backup timer",
            src=path.join(vaultwarden_files_dir, "vaultwarden-backup.timer.j2"),
            dest=path.join(gvars.systemd_unit_dir, "vaultwarden-backup.timer"),
            user="root",
            group="root",
            mode="0444",
            backup_time=vars.vaultwarden_backup_time,
        )

        p.systemd.service(
            name="start backup timer",
            service="vaultwarden-backup.timer",
            running=True,
            enabled=True,
            restarted=backup_timer.changed,
            daemon_reload=backup_service.changed or backup_timer.changed,
        )
