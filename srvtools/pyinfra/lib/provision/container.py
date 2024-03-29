"""
lib/provision/container
-----------------------

This module contains container-related provisioning code.
"""

from os import path
from shlex import quote as shell_quote
from typing import Any, Tuple

from lib.pyinfra import Pyinfra
from ..model.container import Container
from .. import vars

ctr_env_dir = "/usr/local/etc/ctr-env"
_container_inited = False

def container_init(pyinfra: Pyinfra) -> None:
    global _container_inited
    if _container_inited:
        return
    _container_inited = True
    with pyinfra.ctx("container") as p:
        p.files.directory(
            name="configure env directory",
            path=ctr_env_dir,
            present=True,
            user="root",
            group="root",
            mode="0755",
        )


def container_env_file(pyinfra: Pyinfra, ctr: Container) -> Tuple[str, Any]:
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
    ctr_env.update({k: str(v) for k, v in ctr.get_environment(ctr).items()})

    p = pyinfra.ctx("container")
    op = p.files.template(
        name=f"env file: {ctr.name}",
        src=path.join(vars.ctr_files_dir, "container-env.j2"),
        dest=ctr_env_file_path,
        user="root",
        group="root",
        mode="0400",  # env files may contain secrets, so restrict read access
        ctr_env=ctr_env,
        shell_quote=shell_quote,
    )
    return (ctr_env_file_path, op)


def container_user_group(pyinfra: Pyinfra, ctr: Container) -> None:
    """
    Deploys the user and group for the given `ctr`.
    """
    addl_user_args = {
        "group": vars.default_user_group,
    }
    p = pyinfra.ctx("container")
    if ctr.gid is not None:
        group_name = ctr.name
        addl_user_args["group"] = group_name
        p.server.group(
            name=f"create group: {ctr.name}",
            group=group_name,
            gid=ctr.gid,
        )
    if ctr.uid is not None:
        user_name = ctr.name
        p.server.user(
            name=f"create user: {ctr.name}",
            user=user_name,
            shell=vars.nologin_shell,
            comment=f"{ctr.name} container user",
            uid=ctr.uid,
        )
