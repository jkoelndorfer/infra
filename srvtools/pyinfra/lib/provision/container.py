"""
lib/provision/container
-----------------------

This module contains container-related provisioning code.
"""

from os import path
from shlex import quote as shell_quote
from typing import Any, Tuple

from pyinfra.operations import files

from ..model.container import Container
from ..vars import ctr_files_dir

ctr_env_dir = "/usr/local/etc/ctr-env"
_container_inited = False

def container_init() -> None:
    global _container_inited
    if _container_inited:
        return
    _container_inited = True
    files.directory(
        name="[container] configure env directory",
        path=ctr_env_dir,
        present=True,
        user="root",
        group="root",
        mode="0755",
        _sudo=True,
    )  # pyright: ignore


def container_env_file(ctr: Container) -> Tuple[str, Any]:
    """
    Deploys a container environment file for the given `ctr`.
    """
    ctr_env_file_path = path.join(ctr_env_dir, ctr.name)

    # linuxserver docker images use PUID and PGID environment variables
    # to change the user they run as, so we implicitly include them here.
    ctr_env = dict()
    if ctr.uid is not None:
        ctr_env["PUID"] = str(ctr.uid)
    if ctr.gid is not None:
        ctr_env["PGID"] = str(ctr.gid)
    ctr_env.update({k: str(v) for k, v in ctr.get_environment().items()})

    op = files.template(
        name=f"[container] env file: {ctr.name}",
        src=path.join(ctr_files_dir, "container-env.j2"),
        dest=ctr_env_file_path,
        user="root",
        group="root",
        mode="0400", # env files may contain secrets, so restrict read access
        ctr_env=ctr_env,
        shell_quote=shell_quote,
        _sudo=True,
    ) # pyright: ignore
    return (ctr_env_file_path, op)
