"""
tools/switchcfg -- Switch Configuration Renderer
================================================

This script prints the EdgeSwitch CLI commands that configure the VLANs, ports,
SNMP access and remote logging for the homelab.

This script only prints commands to be executed to configure a switch.
"""

import re

import click

from infralib.config.homelab import (
    HomelabNetworking,
    HomelabNetworks,
    HomelabSNMP,
    HomelabSwitch,
    HomelabSwitchPort,
)
from infralib.error import InfralibError, InvalidConfigurationError

from config import load_configuration

# The VLAN a switch starts with. It always exists, and can't be created or renamed.
_DEFAULT_VLAN = 1

_MAX_VLAN_NAME_LENGTH = 32

# The least severe messages the switch sends to the Kubernetes host, as the router
# does.
_SYSLOG_SEVERITY = "notice"
_PORT_PATTERN = re.compile(r"[0-9]+/[0-9]+")

# Quotes would end a quoted value early, and a line break would start a new command.
_UNSAFE_TEXT_PATTERN = re.compile(r"[\"'\x00-\x1f\x7f]")


def _quoted(subject: str, text: str) -> str:
    """
    Quotes text for the switch's CLI, rejecting text that can't be quoted safely.
    """
    if _UNSAFE_TEXT_PATTERN.search(text):
        raise InvalidConfigurationError(
            f"invalid {subject}: {text!r} contains quotes or control characters"
        )
    return f'"{text}"'


def _vlan_list(vlans: set[int]) -> str:
    return ",".join(str(vlan) for vlan in sorted(vlans))


def _untagged_vlan(port: HomelabSwitchPort, networks: HomelabNetworks) -> int | None:
    """
    The VLAN a port carries untagged. A network with no VLAN ID is on the default VLAN.
    """
    if port.untagged is None:
        return None
    return networks.by_name[port.untagged].vlan_id or _DEFAULT_VLAN


def _tagged_vlans(port: HomelabSwitchPort, networks: HomelabNetworks) -> set[int]:
    """
    The VLANs a port carries tagged.
    """
    # HomelabNetworking has already checked that tagged networks have a VLAN ID.
    return {
        vlan_id
        for name in port.tagged
        if (vlan_id := networks.by_name[name].vlan_id) is not None
    }


def _render_vlan_database(vlans: set[int], networks: HomelabNetworks) -> list[str]:
    """
    Renders the commands that create and name VLANs.
    """
    created = vlans - {_DEFAULT_VLAN}
    if not created:
        return []

    lines = ["vlan database"]
    for vlan in sorted(created):
        # Several networks can share a VLAN, and the name should mention each.
        name = "+".join(n.name for n in networks.by_name.values() if n.vlan_id == vlan)
        if len(name) > _MAX_VLAN_NAME_LENGTH:
            raise InvalidConfigurationError(
                f"invalid VLAN {vlan}: name {name!r} is longer than "
                f"{_MAX_VLAN_NAME_LENGTH} characters"
            )
        lines += [f"vlan {vlan}", f"vlan name {vlan} {_quoted(f'VLAN {vlan}', name)}"]
    lines.append("exit")
    return lines


def _render_port(
    switch: HomelabSwitch,
    port: HomelabSwitchPort,
    switch_vlans: set[int],
    networks: HomelabNetworks,
) -> list[str]:
    """
    Renders the commands that configure a port.
    """
    subject = f"switch {switch.name!r} port {port.port!r}"
    if not _PORT_PATTERN.fullmatch(port.port):
        raise InvalidConfigurationError(
            f"invalid {subject}: EdgeSwitch ports look like 0/1"
        )

    untagged = _untagged_vlan(port, networks)
    tagged = _tagged_vlans(port, networks)

    # NOTE: HomelabNetworking can't catch this one, because it doesn't know that a
    # network with no VLAN ID is on the switch's default VLAN.
    if untagged in tagged:
        raise InvalidConfigurationError(
            f"invalid {subject}: VLAN {untagged} is both tagged and untagged"
        )

    carried = tagged if untagged is None else tagged | {untagged}
    excluded = (switch_vlans | {_DEFAULT_VLAN}) - carried

    lines = [f"interface {port.port}"]
    if port.description is not None:
        description = _quoted(f"{subject} description", port.description)
        lines.append(f"description {description}")

    # NOTE: VLANs are added before others are removed, so a port being changed always
    # has the VLANs it needs. This follows the order Ansible's module uses.
    lines += [
        f"vlan participation include {_vlan_list(carried)}",
        f"vlan pvid {_DEFAULT_VLAN if untagged is None else untagged}",
    ]
    if untagged is not None:
        lines.append(f"no vlan tagging {untagged}")
    if tagged:
        lines.append(f"vlan tagging {_vlan_list(tagged)}")
    if excluded:
        lines.append(f"vlan participation exclude {_vlan_list(excluded)}")
    lines.append("exit")
    return lines


def _render_snmp(networking: HomelabNetworking) -> list[str]:
    """
    Renders the commands that grant read-only SNMP access to the Kubernetes host,
    and remove the communities the switch starts with.
    """
    # NOTE: The default private community grants write access. Removing a community
    # that is already gone prints an error, which is harmless.
    return [
        f"snmp-server community {networking.snmp.community} ro "
        f"ipaddress {networking.kubernetes_host}",
        *(f"no snmp-server community {c}" for c in HomelabSNMP.default_communities),
    ]


def _render_logging(networking: HomelabNetworking) -> list[str]:
    """
    Renders the commands that send the switch's logs, at notice and above, to
    VictoriaLogs on the Kubernetes host.
    """
    return [
        f"logging host {networking.kubernetes_host} ipv4 "
        f"{networking.ports.syslog} {_SYSLOG_SEVERITY}",
        "logging syslog",
    ]


def render_switch(switch: HomelabSwitch, networking: HomelabNetworking) -> str:
    """
    Renders the commands that configure a switch, starting from privileged mode.
    """
    networks = networking.networks

    switch_vlans: set[int] = set()
    for port in switch.ports:
        switch_vlans |= _tagged_vlans(port, networks)
        if (untagged := _untagged_vlan(port, networks)) is not None:
            switch_vlans.add(untagged)

    lines = [
        f"! Switch {switch.name}. Paste from privileged mode, reading the output.",
        "! This does not move the management VLAN or run write memory.",
        *_render_vlan_database(switch_vlans, networks),
    ]
    lines += ["configure", *_render_snmp(networking), *_render_logging(networking)]
    for port in switch.ports:
        lines += _render_port(switch, port, switch_vlans, networks)
    lines.append("exit")
    return "\n".join(lines) + "\n"


def render_switches(networking: HomelabNetworking, name: str | None = None) -> str:
    """
    Renders every switch, or only the switch with a given name.
    """
    switches = [s for s in networking.switches if name is None or s.name == name]
    if name is not None and not switches:
        raise InvalidConfigurationError(f"no switch {name!r}")
    return "\n".join(render_switch(s, networking) for s in switches)


@click.command()
@click.argument("switch", required=False)
def main(switch: str | None) -> None:
    """
    Prints the commands that configure SWITCH, or every switch. Applies nothing.
    """
    try:
        networking = load_configuration().homelab.network
        click.echo(render_switches(networking, switch), nl=False)
    except InfralibError as e:
        raise click.ClickException(str(e)) from e


if __name__ == "__main__":
    main()
