"""
roles/edgerouter/provision
--------------------------

This module contains provisioning logic for the edgerouter role.
"""

import re
from os.path import dirname, join as pjoin
from shlex import quote as sv
from typing import Iterable, List

from lib.pyinfra import Pyinfra
from .model import DynDNSConfig
from . import secrets, vars

files_dir = pjoin(dirname(__file__), "files")
ipset_dir = pjoin(files_dir, "ipsets")
ipsets: List[str] = list()


def provision(p: Pyinfra) -> None:
    provision_dyndns(p, secrets.dyndns)
    provision_ipsets(p)
    execute_post_config_d_scripts(p)
    provision_router_cfg(p)


def execute_post_config_d_scripts(p: Pyinfra) -> None:
    p.server.shell(
        name="execute post-config.d scripts",
        commands=['for i in /config/scripts/post-config.d/*; do sudo "$i"; done'],
    )


def provision_ipset(p: Pyinfra, name: str, ipset_entries: Iterable[str]) -> None:
    global ipsets
    ipsets.append(name)

    # Edgerouter will complain if an ipset already exists without having
    # first been defined in its managed configuration. To work around this,
    # we run a script to create the ipset first, using managed configuration.
    p.server.shell(
        name=f"create ipset {name}",
        commands=[f"{sv(vars.scripts_dir)}/create-ipset {sv(name)}"],
    )
    p.files.template(
        name=f"deploy ipset {name}",
        src=pjoin(ipset_dir, "ipset.j2"),
        dest=pjoin(vars.user_data_config_dir, "ipsets", f"{name}.ipset"),
        user=vars.config_user,
        group=vars.config_group,
        mode="0444",
        ipset_name=name,
        ipset_entries=ipset_entries,
    )  # pyright: ignore


def provision_ipsets(pyinfra: Pyinfra) -> None:
    p = pyinfra.ctx("ipsets")
    p.files.put(
        name="deploy ipset restore script",
        src=pjoin(ipset_dir, "restore-ipset"),
        dest=vars.post_config_d_dir,
        user=vars.config_user,
        group=vars.config_group,
        mode="0555",
    )
    p.files.put(
        name="deploy ipset create script",
        src=pjoin(ipset_dir, "create-ipset"),
        dest=vars.scripts_dir,
        user=vars.config_user,
        group=vars.config_group,
        mode="0555",
    )
    ipsets = [
        ("usa-ipv4", read_ips_from_file("usa-ipv4.txt")),
    ]
    for ipset_name, ipset_entries in ipsets:
        provision_ipset(p, ipset_name, ipset_entries)

    for network_group in secrets.wireguard_peers.network_groups():
        provision_ipset(
            p,
            network_group,
            (p.ip for p in secrets.wireguard_peers.in_network_group(network_group)),
        )


def read_ips_from_file(path: str) -> Iterable[str]:
    comment_line = re.compile(r"^\s*#")
    with open(pjoin(ipset_dir, path), "r") as f:
        for ln in f.readlines():
            if comment_line.match(ln):
                continue
            yield ln.strip()


def provision_dyndns(pyinfra: Pyinfra, config: DynDNSConfig) -> None:
    dyndns_files_dir = pjoin(files_dir, "dyndns")
    dyndns_config_dir = pjoin(vars.user_data_config_dir, "dyndns")
    p = pyinfra.ctx("dyndns")
    p.files.template(
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
    )  # pyright: ignore

    p.files.put(
        name="deploy dyndns script",
        src=pjoin(dyndns_files_dir, "dyndns.sh"),
        dest=pjoin(dyndns_config_dir, "dyndns.sh"),
        user=vars.config_user,
        group=vars.config_group,
        mode="0550",
    )


def provision_router_cfg(pyinfra: Pyinfra) -> None:
    reload_config = pjoin(vars.user_data_config_dir, "scripts", "reload-config")
    p = pyinfra.ctx("config")
    p.files.put(
        name="provision config reload script",
        src=pjoin(files_dir, "reload-config"),
        dest=reload_config,
        user=vars.config_user,
        group=vars.config_group,
        mode="0555",
    )
    p.files.template(
        name="deploy router configuration",
        src=pjoin(files_dir, "router-config.j2"),
        dest=vars.router_runtime_cfg,
        user=vars.config_user,
        group=vars.config_group,
        mode="0440",
        str=str,
        secrets=secrets,
        vars=vars,
        ipsets=ipsets,
    )
    p.server.shell(
        name="reload router config",
        commands=[f"sg {sv(vars.config_group)} -c {sv(reload_config)}"],
    )
