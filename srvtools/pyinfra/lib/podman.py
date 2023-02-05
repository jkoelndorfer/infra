"""
lib/podman
----------

This module contains podman-related deployment code.
"""

from os import path
from typing import List, Mapping, Tuple

from pyinfra.operations import files, systemd

from .model.container import Container
from . import vars

_podman_initialized = False


def podman_init():
    files.directory(
        path=vars.ctr_env_dir,
        present=True,
        user="root",
        group="root",
        mode="0755",
    )


def podman_ctr(container: Container):
    global _podman_initialized
    if not _podman_initialized:
        podman_init()
        _podman_initialized = True

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
