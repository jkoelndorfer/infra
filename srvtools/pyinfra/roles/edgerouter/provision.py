"""
roles/edgerouter/provision
--------------------------

This module contains provisioning logic for the edgerouter role.
"""

import re
from os.path import dirname, join as pjoin
from shlex import quote as sv

from pyinfra.operations import files, server

from .model import DynDNSConfig
from . import secrets, vars

files_dir = pjoin(dirname(__file__), "files")
ipset_dir = pjoin(files_dir, "ipsets")

def provision() -> None:
    provision_dyndns(secrets.dyndns)
    provision_ipsets()
    execute_post_config_d_scripts()
    provision_router_cfg()


def execute_post_config_d_scripts() -> None:
    server.shell(
        name="execute post-config.d scripts",
        commands=['for i in /config/scripts/post-config.d/*; do sudo "$i"; done'],
    )


def provision_ipset(name: str) -> None:
    ipset_entries = list()
    comment_line = re.compile(r"^\s*#")
    with open(pjoin(ipset_dir, f"{name}.txt"), "r") as f:
        for l in f.readlines():
            if comment_line.match(l):
                continue
            ipset_entries.append(l)
    files.template(
        name=f"deploy ipset {name}",
        src=pjoin(ipset_dir, "ipset.j2"),
        dest=pjoin(vars.user_data_config_dir, "ipsets", f"{name}.ipset"),
        user=vars.config_user,
        group=vars.config_group,
        mode="0444",
        _sudo=True,
        ipset_name=name,
        ipset_entries=ipset_entries,
    )  # pyright: ignore


def provision_ipsets() -> None:
    files.put(
        name="deploy ipset restore script",
        src=pjoin(ipset_dir, "restore-ipset"),
        dest=vars.post_config_d_dir,
        user=vars.config_user,
        group=vars.config_group,
        mode="0555",
        _sudo=True,
    )
    ipsets = [
        "usa-ipv4"
    ]
    for i in ipsets:
        provision_ipset(i)

def provision_dyndns(config: DynDNSConfig) -> None:
    dyndns_files_dir = pjoin(files_dir, "dyndns")
    dyndns_config_dir = pjoin(vars.user_data_config_dir, "dyndns")
    files.template(
        name="deploy dyndns configuration",
        src=pjoin(dyndns_files_dir, "dyndns-config.j2"),
        dest=pjoin(dyndns_config_dir, "cfg"),
        user=vars.config_user,
        group=vars.config_group,
        mode="0440",
        iface=sv(vars.wan_iface),
        hostname=sv(config.hostname),
        username=sv(config.username),
        password=sv(config.password),
        url=sv(config.url),
        _sudo=True,
    )  # pyright: ignore

    files.put(
        name="deploy dyndns script",
        src=pjoin(dyndns_files_dir, "dyndns.sh"),
        dest=pjoin(dyndns_config_dir, "dyndns.sh"),
        user=vars.config_user,
        group=vars.config_group,
        _sudo=True,
    )

def provision_router_cfg() -> None:
    reload_config = pjoin(vars.user_data_config_dir, "scripts", "reload-config")
    files.put(
        name="provision config reload script",
        src=pjoin(files_dir, "reload-config"),
        dest=reload_config,
        user=vars.config_user,
        group=vars.config_group,
        mode="0555",
        _sudo=True,
    )

    files.template(
        name="deploy router configuration",
        src=pjoin(files_dir, "router-config.j2"),
        dest=vars.router_runtime_cfg,
        user=vars.config_user,
        group=vars.config_group,
        mode="0440",
        secrets=secrets,
        vars=vars,
        _sudo=True,
    ) # pyright: ignore
    server.shell(
        name="reload router config",
        commands=[reload_config],
    ) # pyright: ignore
