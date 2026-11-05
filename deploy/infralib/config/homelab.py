"""
infralib/config/homelab -- Homelab Configuration
================================================

This file defines data types for Homelab-specific configuration.
"""

from collections import Counter
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from ipaddress import IPv4Address, IPv4Interface, IPv4Network
import re
from typing import Any, Self

from ..error import InvalidConfigurationError

_MAC_PATTERN = re.compile(r"[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}")
_ENCRYPTED_PASSWORD_PATTERN = re.compile(r"\$5\$[./0-9A-Za-z]{1,16}\$[./0-9A-Za-z]{43}")
_PORT_FORWARD_PROTOCOLS = ("tcp", "udp", "tcp_udp")


@contextmanager
def _invalid_configuration(subject: str) -> Iterator[None]:
    """
    Raises InvalidConfigurationError in place of errors from malformed values.
    """
    try:
        yield
    except KeyError as e:
        raise InvalidConfigurationError(f"invalid {subject}: missing {e}") from e
    except (InvalidConfigurationError, TypeError, ValueError) as e:
        raise InvalidConfigurationError(f"invalid {subject}: {e}") from e


def _duplicates[T](values: Iterable[T]) -> list[T]:
    """
    Returns each value that appears more than once.
    """
    return [value for value, count in Counter(values).items() if count > 1]


@dataclass
class HomelabDHCPRange:
    """
    The addresses a DHCP server hands out dynamically.
    """

    # The first address handed out.
    start: IPv4Address

    # The last address handed out.
    end: IPv4Address

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise InvalidConfigurationError(
                f"invalid DHCP range: {self.end} is before {self.start}"
            )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabDHCPRange from a dictionary.
        """
        with _invalid_configuration("DHCP range"):
            start = IPv4Address(d["start"])
            end = IPv4Address(d["end"])
        return cls(start, end)


@dataclass
class HomelabDHCPAssignment:
    """
    A device that a DHCP server always gives the same address.
    """

    # The name of the device.
    name: str

    # The device's MAC address, normalized to lowercase.
    mac: str

    # The address assigned to the device.
    ip: IPv4Address

    # The DNS names that resolve to the device.
    dns: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # NOTE: YAML 1.1 reads an unquoted all-decimal MAC that starts with a nonzero
        # digit as a base 60 integer, so this check also catches missing quotes.
        if not isinstance(self.mac, str) or not _MAC_PATTERN.fullmatch(self.mac):
            raise InvalidConfigurationError(
                f"invalid DHCP assignment {self.name!r}: "
                f"{self.mac!r} is not a MAC address; "
                "MAC addresses must be quoted in YAML"
            )

        # A bare string would otherwise be treated as a list of single-letter names.
        if not isinstance(self.dns, list):
            raise InvalidConfigurationError(
                f"invalid DHCP assignment {self.name!r}: dns must be a list"
            )

        self.mac = self.mac.lower()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabDHCPAssignment from a dictionary.
        """
        with _invalid_configuration("DHCP assignment"):
            return cls(d["name"], d["mac"], IPv4Address(d["ip"]), d.get("dns", []))


@dataclass
class HomelabDHCP:
    """
    DHCP configuration for one network.
    """

    # The addresses handed out dynamically. None if the server only hands out
    # assignments.
    range: HomelabDHCPRange | None = None

    # The devices that always get the same address.
    assignments: list[HomelabDHCPAssignment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabDHCP from a dictionary.
        """
        with _invalid_configuration("DHCP configuration"):
            dhcp_range = d.get("range")
            return cls(
                None if dhcp_range is None else HomelabDHCPRange.from_dict(dhcp_range),
                [HomelabDHCPAssignment.from_dict(a) for a in d.get("assignments", [])],
            )


@dataclass
class HomelabNetwork:
    """
    One network in the homelab, as seen by its router.

    VLAN IDs need not be unique, because several subnets can share one VLAN.
    """

    # The name of the network.
    name: str

    # The network's IPv4 subnet.
    ipv4_network: IPv4Network

    # The network's VLAN ID. None if the network is untagged.
    vlan_id: int | None = None

    # The network's DHCP configuration. None if the network has no DHCP server.
    dhcp: HomelabDHCP | None = None

    def __post_init__(self) -> None:
        # bool is a subclass of int, and YAML reads "on" and "yes" as true.
        if self.vlan_id is not None and (
            not isinstance(self.vlan_id, int)
            or isinstance(self.vlan_id, bool)
            or not 1 <= self.vlan_id <= 4094
        ):
            raise InvalidConfigurationError(
                f"invalid homelab network {self.name!r}: "
                f"VLAN ID must be from 1 to 4094, not {self.vlan_id!r}"
            )

        if self.dhcp is not None:
            self._check_dhcp(self.dhcp)

    def _check_dhcp(self, dhcp: HomelabDHCP) -> None:
        """
        Checks a DHCP configuration against this network.
        """
        addresses = [(a.name, a.ip) for a in dhcp.assignments]
        if dhcp.range is not None:
            addresses += [
                ("DHCP range start", dhcp.range.start),
                ("DHCP range end", dhcp.range.end),
            ]
        for subject, address in addresses:
            if address not in self.ipv4_network:
                raise InvalidConfigurationError(
                    f"invalid homelab network {self.name!r}: "
                    f"{subject} address {address} is not in {self.ipv4_network}"
                )

        fields: list[tuple[str, list[Any]]] = [
            ("name", [a.name for a in dhcp.assignments]),
            ("MAC", [a.mac for a in dhcp.assignments]),
            ("IP", [a.ip for a in dhcp.assignments]),
        ]
        for field_name, values in fields:
            if duplicates := _duplicates(values):
                listed = ", ".join(str(d) for d in duplicates)
                raise InvalidConfigurationError(
                    f"invalid homelab network {self.name!r}: "
                    f"duplicate DHCP assignment {field_name}: {listed}"
                )

    @property
    def router_interface(self) -> IPv4Interface:
        """
        The router's interface on this network. The router takes the first host.
        """
        # NOTE: hosts() returns a list for a /32 and a generator otherwise.
        first_host = next(iter(self.ipv4_network.hosts()))
        return IPv4Interface(f"{first_host}/{self.ipv4_network.prefixlen}")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabNetwork from a dictionary.
        """
        with _invalid_configuration("homelab network"):
            name = d["name"]
        with _invalid_configuration(f"homelab network {name!r}"):
            ipv4_network = IPv4Network(d["ipv4_network"])
            dhcp = d.get("dhcp")
            dhcp = None if dhcp is None else HomelabDHCP.from_dict(dhcp)
            vlan_id = d.get("vlan_id")
        return cls(name, ipv4_network, vlan_id, dhcp)


@dataclass
class HomelabDNSRecord:
    """
    DNS names for an address that has no DHCP assignment.
    """

    # The name of the record.
    name: str

    # The address the names resolve to.
    ip: IPv4Address

    # The DNS names that resolve to the address.
    dns: list[str]

    def __post_init__(self) -> None:
        # A bare string would otherwise be treated as a list of single-letter names.
        if not isinstance(self.dns, list):
            raise InvalidConfigurationError(
                f"invalid DNS record {self.name!r}: dns must be a list"
            )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabDNSRecord from a dictionary.
        """
        with _invalid_configuration("DNS record"):
            return cls(d["name"], IPv4Address(d["ip"]), d["dns"])


@dataclass
class HomelabPortForward:
    """
    A port on the router's WAN address that is forwarded to an internal address.
    """

    # What the port forward is for.
    description: str

    # The port on the WAN address.
    src_port: int

    # The address traffic is forwarded to.
    dest_ip: IPv4Address

    # The port traffic is forwarded to.
    dest_port: int

    # The protocol to forward: tcp, udp or tcp_udp.
    protocol: str

    def __post_init__(self) -> None:
        subject = f"invalid port forward {self.description!r}"
        for port in (self.src_port, self.dest_port):
            # bool is a subclass of int, and YAML reads "on" and "yes" as true.
            if (
                not isinstance(port, int)
                or isinstance(port, bool)
                or not 1 <= port <= 65535
            ):
                raise InvalidConfigurationError(
                    f"{subject}: port must be from 1 to 65535, not {port!r}"
                )

        if self.protocol not in _PORT_FORWARD_PROTOCOLS:
            raise InvalidConfigurationError(
                f"{subject}: protocol must be tcp, udp or tcp_udp, "
                f"not {self.protocol!r}"
            )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabPortForward from a dictionary.
        """
        with _invalid_configuration("port forward"):
            return cls(
                d["description"],
                d["src_port"],
                IPv4Address(d["dest_ip"]),
                d["dest_port"],
                d["protocol"],
            )


@dataclass
class HomelabSwitchPort:
    """
    The networks carried by one switch port. Ports not listed are left unmanaged.
    """

    # The switch's identifier for the port. Its format is up to the switch, so it is
    # not validated here.
    port: str

    # The name of the network carried untagged. None if the port only carries tagged
    # traffic.
    untagged: str | None = None

    # The names of the networks carried tagged. Networks that share a VLAN ID share
    # tagging, so only one of them needs to be listed.
    tagged: list[str] = field(default_factory=list)

    # What the port is connected to.
    description: str | None = None

    def __post_init__(self) -> None:
        # A bare string would otherwise be treated as a list of single-letter names.
        if not isinstance(self.tagged, list):
            raise InvalidConfigurationError(
                f"invalid switch port {self.port!r}: tagged must be a list"
            )

        if self.untagged is None and not self.tagged:
            raise InvalidConfigurationError(
                f"invalid switch port {self.port!r}: carries no networks"
            )

        if duplicates := _duplicates(self.tagged):
            listed = ", ".join(duplicates)
            raise InvalidConfigurationError(
                f"invalid switch port {self.port!r}: duplicate tagged network: {listed}"
            )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabSwitchPort from a dictionary.
        """
        with _invalid_configuration("switch port"):
            return cls(
                # YAML reads a bare port number as an integer.
                str(d["port"]),
                d.get("untagged"),
                d.get("tagged", []),
                d.get("description"),
            )


@dataclass
class HomelabSwitch:
    """
    A managed switch, and the networks carried by its ports.
    """

    # The name of the switch.
    name: str

    # The switch's managed ports.
    ports: list[HomelabSwitchPort] = field(default_factory=list)

    def __post_init__(self) -> None:
        if duplicates := _duplicates(p.port for p in self.ports):
            listed = ", ".join(duplicates)
            raise InvalidConfigurationError(
                f"invalid switch {self.name!r}: duplicate port: {listed}"
            )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabSwitch from a dictionary.
        """
        with _invalid_configuration("switch"):
            return cls(
                d["name"],
                [HomelabSwitchPort.from_dict(p) for p in d.get("ports", [])],
            )


def _require_secret(subject: str, name: str, value: Any) -> None:
    """
    Checks that a secret is a non-empty string, without revealing its value.
    """
    if not isinstance(value, str) or not value:
        raise InvalidConfigurationError(
            f"invalid {subject}: {name} must be a non-empty string"
        )


@dataclass
class HomelabRouterAdmin:
    """
    The router's administrator account.
    """

    # The name the administrator logs in with.
    username: str

    # The administrator's full name.
    full_name: str

    # The hash of the administrator's password, in the form sha256_crypt produces. The
    # router does not support specifying the number of hash rounds, so the hash must
    # use the implicit 5000.
    encrypted_password: str = field(repr=False)

    # The administrator's SSH public key: its type and key, with no comment.
    pubkey: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.encrypted_password, str
        ) or not _ENCRYPTED_PASSWORD_PATTERN.fullmatch(self.encrypted_password):
            raise InvalidConfigurationError(
                "invalid router admin: encrypted_password must be a sha256_crypt hash "
                "with implicit rounds"
            )

        if not isinstance(self.pubkey, str) or len(self.pubkey.split(" ")) != 2:
            raise InvalidConfigurationError(
                "invalid router admin: pubkey must be a type and a key, with no comment"
            )

    @property
    def pubkey_type(self) -> str:
        """
        The type of the administrator's SSH public key.
        """
        return self.pubkey.split(" ")[0]

    @property
    def pubkey_key(self) -> str:
        """
        The key of the administrator's SSH public key.
        """
        return self.pubkey.split(" ")[1]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabRouterAdmin from a dictionary.
        """
        with _invalid_configuration("router admin"):
            return cls(
                d["username"], d["full_name"], d["encrypted_password"], d["pubkey"]
            )


@dataclass
class HomelabPPPoE:
    """
    The credentials the router uses to connect to the ISP over PPPoE.
    """

    # The PPPoE username.
    username: str

    # The PPPoE password.
    password: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_secret("router PPPoE", "password", self.password)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabPPPoE from a dictionary.
        """
        with _invalid_configuration("router PPPoE"):
            return cls(d["username"], d["password"])


@dataclass
class HomelabRouter:
    """
    Configuration only used to provision the router.

    NOTE: This holds credentials. Do not pass any of it to a Pulumi resource, or it
    will end up in state.
    """

    # The router's administrator account.
    admin: HomelabRouterAdmin

    # The credentials for the connection to the ISP.
    pppoe: HomelabPPPoE

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabRouter from a dictionary.
        """
        with _invalid_configuration("homelab router"):
            return cls(
                HomelabRouterAdmin.from_dict(d["admin"]),
                HomelabPPPoE.from_dict(d["pppoe"]),
            )


@dataclass
class HomelabNetworks:
    """
    The homelab's networks. Each is configured with its attribute's name.
    """

    # The network for administering everything else.
    mgmt: HomelabNetwork

    # A way back in if mgmt breaks. It has the same access as mgmt, but only exists on
    # the router, so that a broken switch or VLAN configuration can't take it down too.
    mgmt_backup: HomelabNetwork

    # The network servers are attached to.
    infra: HomelabNetwork

    # The network that switches and access points are managed on. Devices on the same
    # VLAN reach these directly, without passing through the router's firewall, so only
    # network equipment belongs here.
    net_infra: HomelabNetwork

    # The network for devices that need access to most internal services.
    trusted: HomelabNetwork

    # The default network for everything else, with access to few internal services.
    untrusted: HomelabNetwork

    # The network for bad actors. DNS is forcibly redirected to internal DNS, and no
    # other internal services are reachable. Examples include Roku TVs, which ignore
    # DHCP-prescribed DNS.
    lockdown: HomelabNetwork

    # The network WireGuard peers with the same access as trusted are attached to.
    wireguard_trusted: HomelabNetwork

    # The network shared between the router and the modem.
    modem: HomelabNetwork

    # The network Kubernetes assigns pod addresses from.
    kube_cluster: HomelabNetwork

    # The network Kubernetes assigns service addresses from.
    kube_service: HomelabNetwork

    @property
    def by_name(self) -> dict[str, HomelabNetwork]:
        """
        Every network, keyed by name.
        """
        networks = [
            self.mgmt,
            self.mgmt_backup,
            self.infra,
            self.net_infra,
            self.trusted,
            self.untrusted,
            self.lockdown,
            self.wireguard_trusted,
            self.modem,
            self.kube_cluster,
            self.kube_service,
        ]
        return {network.name: network for network in networks}

    @classmethod
    def from_list(cls, networks: list[dict[str, Any]]) -> Self:
        """
        Constructs a HomelabNetworks from a list of dictionaries. Every network must be
        listed exactly once, and no others may be.
        """
        with _invalid_configuration("homelab networks"):
            parsed = [HomelabNetwork.from_dict(n) for n in networks]

            names = [network.name for network in parsed]
            if duplicates := _duplicates(names):
                raise ValueError(f"duplicate network: {', '.join(duplicates)}")

            expected = [f.name for f in fields(cls)]
            if missing := [name for name in expected if name not in names]:
                raise KeyError(", ".join(missing))
            if unknown := [name for name in names if name not in expected]:
                raise ValueError(f"unknown network: {', '.join(unknown)}")

            return cls(**{network.name: network for network in parsed})


@dataclass(frozen=True)
class HomelabPorts:
    """
    The well-known ports that homelab services are reached on, by name. These are
    fixed by the protocols and devices involved, so they are not read from
    configuration.
    """

    # SSH, which the router is administered over.
    ssh: int = 22

    # DNS, served by the router and by the internal DNS server.
    dns: int = 53

    # DHCP, served by the router.
    dhcp: int = 67

    # HTTP, served by the ingress controller to redirect to HTTPS.
    http: int = 80

    # HTTPS, served by the ingress controller.
    https: int = 443

    # The Syncthing sync protocol.
    syncthing: int = 22000

    # The port UniFi devices report to the controller on.
    unifi_device: int = 8080

    # The port UniFi devices use for STUN with the controller.
    unifi_stun: int = 3478

    # The port UniFi access points are discovered on.
    unifi_ap_discovery: int = 10001

    # WireGuard, for peers attached to the wireguard_trusted network.
    wireguard_trusted: int = 51820


@dataclass
class HomelabNetworking:
    """
    Configuration for everything network-related in the homelab.
    """

    # The DNS servers that the site resolves names through.
    upstream_dns: list[IPv4Address]

    # The homelab's networks.
    networks: HomelabNetworks

    # Configuration only used to provision the router.
    router: HomelabRouter

    # The managed switches.
    switches: list[HomelabSwitch] = field(default_factory=list)

    # DNS names for addresses that have no DHCP assignment.
    dns_records: list[HomelabDNSRecord] = field(default_factory=list)

    # The ports forwarded from the router's WAN address.
    port_forwards: list[HomelabPortForward] = field(default_factory=list)

    # The well-known ports that homelab services are reached on.
    ports: HomelabPorts = field(default_factory=HomelabPorts)

    def __post_init__(self) -> None:
        if duplicates := _duplicates(s.name for s in self.switches):
            listed = ", ".join(duplicates)
            raise InvalidConfigurationError(f"duplicate switch: {listed}")

        if duplicates := _duplicates(r.name for r in self.dns_records):
            listed = ", ".join(duplicates)
            raise InvalidConfigurationError(f"duplicate DNS record: {listed}")

        for switch in self.switches:
            for port in switch.ports:
                self._check_switch_port(switch, port)

    def _check_switch_port(
        self, switch: HomelabSwitch, port: HomelabSwitchPort
    ) -> None:
        """
        Checks that a switch port refers to networks it is able to carry.
        """
        subject = f"invalid switch {switch.name!r} port {port.port!r}"
        networks = self.networks.by_name

        names = [*port.tagged, *([] if port.untagged is None else [port.untagged])]
        for name in names:
            if name not in networks:
                raise InvalidConfigurationError(f"{subject}: no network {name!r}")

        tagged_vlans = {networks[name].vlan_id for name in port.tagged}
        if None in tagged_vlans:
            raise InvalidConfigurationError(
                f"{subject}: tagged networks must have a VLAN ID"
            )

        # NOTE: An untagged network may have no VLAN ID, because it may not have moved
        # off of the switch's default VLAN yet.
        if (
            port.untagged is not None
            and networks[port.untagged].vlan_id in tagged_vlans
        ):
            raise InvalidConfigurationError(
                f"{subject}: VLAN {networks[port.untagged].vlan_id} "
                "is both tagged and untagged"
            )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs a HomelabNetworking from a dictionary.
        """
        with _invalid_configuration("homelab networking"):
            return cls(
                upstream_dns=[IPv4Address(a) for a in d["upstream_dns"]],
                networks=HomelabNetworks.from_list(d["networks"]),
                router=HomelabRouter.from_dict(d["router"]),
                switches=[HomelabSwitch.from_dict(s) for s in d.get("switches", [])],
                dns_records=[
                    HomelabDNSRecord.from_dict(r) for r in d.get("dns_records", [])
                ],
                port_forwards=[
                    HomelabPortForward.from_dict(p) for p in d.get("port_forwards", [])
                ],
            )


class Homelab:
    """
    Configuration for my homelab.
    """

    def __init__(self, kubernetes_context: str, network: HomelabNetworking) -> None:
        # The Kubernetes context used to manage the homelab Kubernetes cluster.
        self.kubernetes_context = kubernetes_context

        # The homelab's networking.
        self.network = network

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        with _invalid_configuration("homelab"):
            return cls(
                d["kubernetes_context"],
                HomelabNetworking.from_dict(d["network"]),
            )
