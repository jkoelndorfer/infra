"""
lib/podman
----------

This module contains podman-related deployment code.
"""

from os import path
from typing import List, Mapping, Tuple

from pyinfra.operations import files, systemd

from . import vars


class Volume:
    def __init__(self, src: str, dest: str) -> None:
        self.src = src
        self.dest = dest


class Container:
    def __init__(
        self,
        name: str,
        image: str,
        environment: Mapping[str, str],
        volumes: List[Volume],
        network: str,
        restart: str,
        max_restarts: int,
        restart_sec: int,
    ) -> None:
        self.name = name
        self.image = image
        self.environment = environment
        self.volumes = volumes
        self.network = network
        self.restart = restart
        self.max_restarts = max_restarts
        self.restart_sec = restart_sec


def podman_init():
    files.directory(
        path=vars.ctr_env_dir,
        present=True,
        user="root",
        group="root",
        mode="0755",
    )


def podman_ctr(container: Container):
    systemd_unit_src_file = path.join(vars.files_dir, "podman-container.j2")
    service_name = container.name
    ctr_env_file = path.join(vars.ctr_env_dir, container.name)
    systemd_unit_template = files.template(
        name=f"podman container systemd unit: {container.name}",
        src=systemd_unit_src_file,
        dest=path.join(vars.systemd_unit_dir, f"{service_name}.service"),
        user="root",
        group="root",
        mode="0444",
        ctr=container,
        ctr_env_file=ctr_env_file,
    )  # pyright: ignore

    if systemd_unit_template.changed:
        systemd.service(service_name, restarted=True, reloaded=True)
