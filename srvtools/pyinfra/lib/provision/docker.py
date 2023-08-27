"""
lib/provision/docker
--------------------

This module contains docker-related provisioning code.
"""

from os import path
from typing import Literal

from .container import container_init, container_env_file, container_user_group
from ..model.container import Container, ContainerNetwork
from ..pyinfra import Pyinfra
from .. import vars


_docker_inited = False


def _vol_owner(owner: Literal["root", "ctr"], ctr_value: str) -> str:
    if owner == "root":
        return "root"
    elif owner == "ctr":
        return ctr_value
    raise ValueError(f"invalid container volume owner: {owner}")


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
    force_restart = False

    p = pyinfra.ctx("docker")
    ctr_env_file, ctr_env_file_op = container_env_file(p, ctr)
    if ctr_env_file_op.changed:
        force_restart = True
    container_user_group(p, ctr)
    for v in ctr.volumes:
        # If the volume source is not an absolute path, it is a
        # named volume.
        #
        # We can't configure ownership or mode on a named volume.
        if not path.isabs(v.src):
            continue
        volume_dir_op = p.files.directory(
            name=f"container volume dir: {v.src}",
            path=v.src,
            user=_vol_owner(v.user, str(ctr.uid or "root")),
            group=_vol_owner(v.group, str(ctr.gid or "root")),
            mode=v.mode,
        )
        if volume_dir_op.changed:
            force_restart = True
        for sd in v.subdirs:
            sd_abs = path.join(v.src, sd.path)
            sd_op = p.files.directory(
                name=f"container volume subdir: {sd_abs}",
                path=sd_abs,
                user=_vol_owner(sd.user, str(ctr.uid or "root")),
                group=_vol_owner(sd.group, str(ctr.gid or "root")),
                mode=sd.mode,
            )
            if sd_op.changed:
                force_restart = True
    if ctr.deploy_config is not None and ctr.deploy_config(p, ctr):
        force_restart = True
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
    if ctr_systemd_unit.changed:
        force_restart = True
    ctr_systemd_service = p.systemd.service(
        name=f"systemd service: {ctr.name}",
        service=systemd_service_name,
        running=True,
        enabled=True,
        restarted=force_restart,
        daemon_reload=ctr_systemd_unit.changed,
    )
    return ctr_systemd_service.changed
