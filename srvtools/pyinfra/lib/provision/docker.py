"""
lib/provision/docker
--------------------

This module contains docker-related provisioning code.
"""

from os import path

from .container import container_init, container_env_file, container_user_group
from ..model.container import Container, ContainerNetwork
from ..pyinfra import Pyinfra
from .. import vars


_docker_inited = False


def docker_init(pyinfra: Pyinfra):
    global _docker_inited
    if _docker_inited:
        return
    _docker_inited = True

    p = pyinfra.ctx("docker")
    p.files.put(
        name="docker-multinet-run",
        src=path.join(vars.docker_files_dir, "docker-multinet-run"),
        dest="/usr/local/sbin/docker-multinet-run",
        user="root",
        group="root",
        mode="0555",
    )

    p.files.put(
        name="docker-network-destroy",
        src=path.join(vars.docker_files_dir, "docker-network-destroy"),
        dest="/usr/local/sbin/docker-network-destroy",
        user="root",
        group="root",
        mode="0555",
    )


def docker_network(pyinfra: Pyinfra, network: ContainerNetwork) -> bool:
    """
    Configures the container network given by `network`.
    """
    docker_init(pyinfra)
    p = pyinfra.ctx("docker")
    network_systemd_unit = p.files.template(
        name=f"network systemd unit: {network.name}",
        src=path.join(vars.docker_files_dir, "docker-network.service.j2"),
        dest=path.join(vars.systemd_unit_dir, network.systemd_service_name),
        user="root",
        group="root",
        mode="0444",
        network=network,
        str=str,
    )
    network_systemd_service = p.systemd.service(
        name=f"systemd service: {network.systemd_service_name}",
        service=network.systemd_service_name,
        running=True,
        enabled=True,
        restarted=network_systemd_unit.changed,
        daemon_reload=network_systemd_unit.changed,
    )

    return network_systemd_unit.changed or network_systemd_service.changed


def docker_ctr(pyinfra: Pyinfra, ctr: Container) -> bool:
    """
    Runs the container given by `ctr` and configures `ctr` to start at system boot.
    """
    container_init(pyinfra)
    docker_init(pyinfra)

    p = pyinfra.ctx("docker")
    ctr_env_file, ctr_env_file_op = container_env_file(p, ctr)
    container_user_group(p, ctr)
    systemd_service_name = f"{ctr.name}.service"
    ctr_systemd_unit = p.files.template(
        name=f"container systemd unit: {ctr.name}",
        src=path.join(vars.docker_files_dir, "docker-container.service.j2"),
        dest=path.join(vars.systemd_unit_dir, systemd_service_name),
        user="root",
        group="root",
        mode="0444",
        dns=vars.home_router_ip,  # TODO: Configure a local, caching resolver for docker containers
        ctr=ctr,
        ctr_env_file=ctr_env_file,
    )
    ctr_systemd_service = p.systemd.service(
        name=f"systemd service: {ctr.name}",
        service=systemd_service_name,
        running=True,
        enabled=True,
        restarted=ctr_systemd_unit.changed or ctr_env_file_op.changed,
        daemon_reload=ctr_systemd_unit.changed,
    )
    return ctr_systemd_unit.changed or ctr_systemd_service.changed
