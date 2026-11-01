"""
provision/roles/edgerouter/provision -- EdgeRouter Provisioning
===============================================================

This module contains provisioning logic for the edgerouter role.
"""

from pathlib import Path
from shlex import quote
from typing import Any

from jinja2 import Template
from pyinfra.api.util import get_template
from pyinfra.operations import files, server

from infralib import InfrastructureConfiguration
from infralib.config.homelab import HomelabDynDNS, HomelabNetworking

_FILES = Path(__file__).parent / "files"
_IPSET_FILES = _FILES / "ipsets"
_ROUTER_TEMPLATE = _FILES / "router-config.j2"

_JINJA_ENV_KWARGS: dict[str, Any] = {"lstrip_blocks": True, "trim_blocks": True}

_CONFIG_DIR = "/config"
_USER_DATA_DIR = f"{_CONFIG_DIR}/user-data"
_SCRIPTS_DIR = f"{_CONFIG_DIR}/scripts"
_ROUTER_CONFIG = f"{_CONFIG_DIR}/config.pyinfra"

_CONFIG_USER = "root"
_CONFIG_GROUP = "vyattacfg"


def provision(config: InfrastructureConfiguration) -> None:
    """
    Provisions the router.
    """
    networking = config.homelab.network

    _provision_dyndns(networking.router.dyndns)
    _provision_ipsets()
    _execute_post_config_scripts()
    _provision_router_config(networking)


def router_template() -> Template:
    """
    Returns the router configuration template, with the options pyinfra renders it with.
    It takes the homelab's networking configuration as `network`.
    """
    return get_template(str(_ROUTER_TEMPLATE), _JINJA_ENV_KWARGS)


def _execute_post_config_scripts() -> None:
    server.shell(
        name="execute post-config.d scripts",
        commands=[f'for i in {_SCRIPTS_DIR}/post-config.d/*; do sudo "$i"; done'],
        _sudo=True,
    )


def _ipset_entries(path: Path) -> list[str]:
    """
    Reads the entries of an ipset from a file, leaving out comments.
    """
    lines = path.read_text().splitlines()
    return [line.strip() for line in lines if not line.lstrip().startswith("#")]


def _provision_ipsets() -> None:
    files.put(
        name="deploy ipset restore script",
        src=str(_IPSET_FILES / "restore-ipset"),
        dest=f"{_SCRIPTS_DIR}/post-config.d/restore-ipset",
        user=_CONFIG_USER,
        group=_CONFIG_GROUP,
        mode="0555",
        _sudo=True,
    )
    files.put(
        name="deploy ipset create script",
        src=str(_IPSET_FILES / "create-ipset"),
        dest=f"{_SCRIPTS_DIR}/create-ipset",
        user=_CONFIG_USER,
        group=_CONFIG_GROUP,
        mode="0555",
        _sudo=True,
    )

    # NOTE: Every ipset needs a network group of the same name in the router
    # configuration template.
    for path in sorted(_IPSET_FILES.glob("*.txt")):
        ipset = path.stem

        # NOTE: The router complains if an ipset exists without having first been
        # defined in its managed configuration, so that has to happen first.
        server.shell(
            name=f"create ipset {ipset}",
            commands=[f"{_SCRIPTS_DIR}/create-ipset {quote(ipset)}"],
            _sudo=True,
        )
        files.template(
            name=f"deploy ipset {ipset}",
            src=str(_IPSET_FILES / "ipset.j2"),
            dest=f"{_USER_DATA_DIR}/ipsets/{ipset}.ipset",
            user=_CONFIG_USER,
            group=_CONFIG_GROUP,
            mode="0444",
            jinja_env_kwargs=_JINJA_ENV_KWARGS,
            ipset_name=ipset,
            ipset_entries=_ipset_entries(path),
            _sudo=True,
        )


def _provision_dyndns(dyndns: HomelabDynDNS) -> None:
    files.template(
        name="deploy dyndns configuration",
        src=str(_FILES / "dyndns" / "dyndns-config.j2"),
        dest=f"{_USER_DATA_DIR}/dyndns/cfg",
        user=_CONFIG_USER,
        group=_CONFIG_GROUP,
        mode="0440",
        jinja_env_kwargs=_JINJA_ENV_KWARGS,
        hostname=quote(dyndns.hostname),
        username=quote(dyndns.username),
        password=quote(dyndns.password),
        url=quote(dyndns.url),
        _sudo=True,
    )
    files.put(
        name="deploy dyndns script",
        src=str(_FILES / "dyndns" / "dyndns.sh"),
        dest=f"{_USER_DATA_DIR}/dyndns/dyndns.sh",
        user=_CONFIG_USER,
        group=_CONFIG_GROUP,
        mode="0550",
        _sudo=True,
    )


def _provision_router_config(networking: HomelabNetworking) -> None:
    reload_config = f"{_USER_DATA_DIR}/scripts/reload-config"

    files.put(
        name="deploy config reload script",
        src=str(_FILES / "reload-config"),
        dest=reload_config,
        user=_CONFIG_USER,
        group=_CONFIG_GROUP,
        mode="0555",
        _sudo=True,
    )
    files.template(
        name="deploy router configuration",
        src=str(_ROUTER_TEMPLATE),
        dest=_ROUTER_CONFIG,
        user=_CONFIG_USER,
        group=_CONFIG_GROUP,
        mode="0440",
        jinja_env_kwargs=_JINJA_ENV_KWARGS,
        network=networking,
        _sudo=True,
    )
    server.shell(
        name="reload router configuration",
        commands=[f"sg {quote(_CONFIG_GROUP)} -c {quote(reload_config)}"],
        _sudo=True,
    )
