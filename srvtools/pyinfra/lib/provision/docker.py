"""
lib/provision/docker
--------------------

This module contains docker-related provisioning code.
"""

from pyinfra.operations import files

from .container import container_init, container_env_file
from ..model.container import Container

def docker_ctr(ctr: Container):
    """
    Runs the container given by `ctr` and configures `ctr` to start at system boot.
    """
    container_init()

    ctr_env_file, _ = container_env_file(ctr)
    ctr_systemd_unit_template = files.template(
        name=f"[podman] container systemd unit: {ctr.name}",
        src=path.join(vars.podman_files_dir, "podman-container.service.j2"),
        dest=path.join(vars.systemd_unit_dir, f"{service_name}.service"),
        user="root",
        group="root",
        mode="0444",
        ctr=ctr,
        ctr_env_file=ctr_env_file,
        _sudo=True,
    )  # pyright: ignore
