"""
lib/provision/docker
--------------------

This module contains docker-related provisioning code.
"""

from os import path

from pyinfra.operations import files, systemd

from .container import container_init, container_env_file
from ..model.container import Container, ContainerNetwork
from .. import vars


_docker_inited = False


def docker_init():
    global _docker_inited
    if _docker_inited:
        return
    _docker_inited = True
    files.put(
        name="[docker] docker-multinet-run",
        src=path.join(vars.docker_files_dir, "docker-multinet-run"),
        dest="/usr/local/sbin/docker-multinet-run",
        user="root",
        group="root",
        mode="0555",
        _sudo=True,
    )

    files.put(
        name="[docker] docker-network-destroy",
        src=path.join(vars.docker_files_dir, "docker-network-destroy"),
        dest="/usr/local/sbin/docker-network-destroy",
        user="root",
        group="root",
        mode="0555",
        _sudo=True,
    )


def docker_network(network: ContainerNetwork) -> bool:
    """
    Configures the container network given by `network`.
    """
    docker_init()
    network_systemd_unit = files.template(
        name=f"[docker] network systemd unit: {network.name}",
        src=path.join(vars.docker_files_dir, "docker-network.service.j2"),
        dest=path.join(vars.systemd_unit_dir, network.systemd_service_name),
        user="root",
        group="root",
        mode="0444",
        network=network,
        str=str,
        _sudo=True,
    )  # pyright: ignore
    network_systemd_service = systemd.service(
        name=f"[docker] systemd service: {network.systemd_service_name}",
        service=network.systemd_service_name,
        running=True,
        enabled=True,
        restarted=network_systemd_unit.changed,
        daemon_reload=network_systemd_unit.changed,
        _sudo=True,
    )  # pyright: ignore

    return network_systemd_unit.changed or network_systemd_service.changed


def docker_ctr(ctr: Container) -> bool:
    """
    Runs the container given by `ctr` and configures `ctr` to start at system boot.
    """
    container_init()
    docker_init()

    ctr_env_file, ctr_env_file_op = container_env_file(ctr)
    systemd_service_name = f"{ctr.name}.service"
    ctr_systemd_unit = files.template(
        name=f"[docker] container systemd unit: {ctr.name}",
        src=path.join(vars.docker_files_dir, "docker-container.service.j2"),
        dest=path.join(vars.systemd_unit_dir, systemd_service_name),
        user="root",
        group="root",
        mode="0444",
        dns=vars.home_router_ip,  # TODO: Configure a local, caching resolver for docker containers
        ctr=ctr,
        ctr_env_file=ctr_env_file,
        _sudo=True,
    )  # pyright: ignore
    ctr_systemd_service = systemd.service(
        name=f"[docker] systemd service: {ctr.name}",
        service=systemd_service_name,
        running=True,
        enabled=True,
        restarted=ctr_systemd_unit.changed or ctr_env_file_op.changed,
        daemon_reload=ctr_systemd_unit.changed,
        _sudo=True,
    )  # pyright: ignore
    return ctr_systemd_unit.changed or ctr_systemd_service.changed
