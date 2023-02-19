"""
lib/podman
----------

This module contains podman-related deployment code.
"""

from os import path
from shlex import quote as shell_quote
from typing import Any, Dict

from pyinfra.operations import files, systemd

from .model.container import Container, ContainerNetwork
from . import vars

_podman_initialized = False

# As podman containers are configured, their networks will also
# be configured. Containers can share networks, so a single network
# may be present in the configuration of multiple containers.
#
# We only want to configure each network once. To facilitate that,
# we track each network that has been configured here as containers
# are set up.
_podman_networks: Dict[str, ContainerNetwork] = dict()

# Aside from tracking the networks that are created per-container,
# we also need to track if they are changed by the pyinfra run.
# If a network is changed, all dependent containers will need to
# be restarted.
_podman_network_changes: Dict[str, Any] = dict()

podman_files_dir = path.join(vars.files_dir, "podman")

def podman_init():
    files.directory(
        name="podman container env directory",
        path=vars.ctr_env_dir,
        present=True,
        user="root",
        group="root",
        mode="0755",
        _sudo=True,
    )


def podman_ctr(ctr: Container):
    global _podman_initialized
    if not _podman_initialized:
        podman_init()
        _podman_initialized = True

    service_name = ctr.name
    ctr_env = dict()
    if ctr.uid is not None:
        ctr_env["PUID"] = str(ctr.uid)
    if ctr.gid is not None:
        ctr_env["PGID"] = str(ctr.gid)
    ctr_env.update({k: str(v) for k, v in ctr.get_environment().items()})

    ctr_env_file = path.join(vars.ctr_env_dir, ctr.name)
    ctr_env_template = files.template(
        name=f"podman container env file: {ctr.name}",
        src=path.join(podman_files_dir, "container-env.j2"),
        dest=ctr_env_file,
        user="root",
        group="root",
        mode="0400", # env files may contain secrets, so restrict read access
        ctr_env=ctr_env,
        shell_quote=shell_quote,
        _sudo=True,
    ) # pyright: ignore

    # Don't restart the service container unless we have to.
    #
    # Circumstances that would necessitate a container restart are:
    #
    # * Environment variables for the service have changed
    # * The systemd unit file for running the service has changed
    # * One or more networks for the container have been changed or restarted
    ctr_restarted = False

    for network in ctr.networks:
        if _podman_network(network):
            ctr_restarted = True

    ctr_systemd_unit_template = files.template(
        name=f"podman container systemd unit: {ctr.name}",
        src=path.join(podman_files_dir, "podman-container.service.j2"),
        dest=path.join(vars.systemd_unit_dir, f"{service_name}.service"),
        user="root",
        group="root",
        mode="0444",
        ctr=ctr,
        ctr_env_file=ctr_env_file,
        network_service_name=_podman_network_service_name,
        _sudo=True,
    )  # pyright: ignore

    if ctr_env_template.changed or ctr_systemd_unit_template.changed:
        ctr_restarted = True

    # TODO: Remove this return
    # Don't start the service -- we wanna see if this stuff actually gets provisioned
    # right, first.
    return
    systemd.service(
        name=f"podman container service restart: {ctr.name}",
        service=service_name,
        running=True,
        restarted=ctr_restarted,
        daemon_reload=True,
        _sudo=True,
    ) # pyright: ignore


def _podman_network(network: ContainerNetwork) -> bool:
    existing_network = _podman_networks.get(network.name, None)
    if existing_network is not None:
        if existing_network != network:
            # A network with network.name already exists, and it doesn't
            # match the network we're attempting to configure. This is
            # an impossible-to-satisfy configuration.
            raise Exception(f"podman network conflict: {existing_network} conflicts with {network}")
        else:
            # The network has already been configured; there is nothing to do.
            return _podman_network_changes[network.name]
    _podman_networks[network.name] = network

    network_systemd_template = files.template(
        name=f"podman network systemd unit: {network.name}",
        src=path.join(podman_files_dir, "podman-network.service.j2"),
        dest=path.join(vars.systemd_unit_dir, _podman_network_service_name(network)),
        user="root",
        group="root",
        mode="0444",
        network=network,
        shell_quote=shell_quote,
        _sudo=True,
    ) # pyright: ignore

    network_systemd_service = systemd.service(
        name=f"podman network systemd service: {network.name}",
        service=_podman_network_service_name(network),
        running=True,
        restarted=network_systemd_template.changed,
        daemon_reload=True,
        _sudo=True,
    )  # pyright: ignore
    _podman_network_changes[network.name] = network_systemd_template.changed or network_systemd_service.changed
    return _podman_network_changes[network.name]


def _podman_network_service_name(network: ContainerNetwork) -> str:
    return f"podman-network-{network.name}.service"
