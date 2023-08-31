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

from lib.pyinfra import Pyinfra
from .containers import service_containers, syncthing_container, vaultwarden_container
from .containerlib import swag_networks
from . import vars


def provision(p: Pyinfra):
    provision_aqgo(p)
    provision_container_networks(p)
    provision_service_containers(p)
    provision_rclone_backup(p)
    provision_vaultwarden_backup(p)


def provision_aqgo(pyinfra: Pyinfra):
    aqgo_files_dir = path.join(vars.files_dir, "aqgo")
    p = pyinfra.ctx("aqgo")

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
    p = pyinfra.ctx("rclone")

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
        backup_working_dir=syncthing_container.data_dir,
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


def provision_service_containers(p: Pyinfra):
    for ctr in service_containers:
        docker_ctr(p, ctr)


def provision_vaultwarden_backup(pyinfra: Pyinfra):
    vaultwarden_files_dir = path.join(vars.files_dir, "vaultwarden")
    vaultwarden_syncthing_data = path.join(syncthing_container.volume_named("data").src, vaultwarden_container.name)

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
            vaultwarden_data_dir=vaultwarden_container.volume_named("data").src,
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
