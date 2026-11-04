"""
tests/infralib/config/test_homelab -- Homelab Configuration Tests
=================================================================

This file contains code to test homelab configuration.
"""

from ipaddress import IPv4Address, IPv4Interface, IPv4Network
from typing import Any

import pytest
from yaml import safe_load as yaml_safe_load

from infralib.config.homelab import (
    Homelab,
    HomelabDHCP,
    HomelabDHCPAssignment,
    HomelabDHCPRange,
    HomelabDNSRecord,
    HomelabDynDNS,
    HomelabNetwork,
    HomelabNetworking,
    HomelabNetworks,
    HomelabPortForward,
    HomelabPorts,
    HomelabPPPoE,
    HomelabRouter,
    HomelabRouterAdmin,
    HomelabSwitch,
    HomelabSwitchPort,
)
from infralib.error import InvalidConfigurationError
from infralib.testing import dummy_infrastructure_configuration


NETWORK_ATTRIBUTES = [
    "trusted",
    "wireguard_trusted",
    "modem",
    "kube_cluster",
    "kube_service",
    "infra",
    "mgmt",
    "mgmt_backup",
    "net_infra",
    "lockdown",
    "untrusted",
]


@pytest.fixture
def assignment_dict() -> dict[str, Any]:
    return {
        "name": "host-a",
        "mac": "00:00:5E:00:53:01",
        "ip": "10.0.12.5",
        "dns": ["host-a.lan"],
    }


@pytest.fixture
def network_dict(assignment_dict: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "trusted",
        "ipv4_network": "10.0.12.0/23",
        "vlan_id": 12,
        "dhcp": {
            "range": {"start": "10.0.12.10", "end": "10.0.12.250"},
            "assignments": [assignment_dict],
        },
    }


@pytest.fixture
def networking_dict(
    network_dict: dict[str, Any], router_dict: dict[str, Any]
) -> dict[str, Any]:
    return {
        "upstream_dns": ["192.0.2.53", "198.51.100.53"],
        "router": router_dict,
        "networks": [
            network_dict,
            {"name": "wireguard_trusted", "ipv4_network": "10.0.15.0/24"},
            {"name": "modem", "ipv4_network": "10.0.1.0/24"},
            {"name": "kube_cluster", "ipv4_network": "10.0.16.0/22"},
            {"name": "kube_service", "ipv4_network": "10.0.8.0/22"},
            {
                "name": "infra",
                "ipv4_network": "10.0.2.0/24",
                "dhcp": {"assignments": []},
            },
            {"name": "mgmt", "ipv4_network": "10.0.4.0/22"},
            {"name": "mgmt_backup", "ipv4_network": "10.0.3.0/24"},
            {"name": "net_infra", "ipv4_network": "10.0.20.0/24", "vlan_id": 20},
            {"name": "lockdown", "ipv4_network": "10.0.21.0/24", "vlan_id": 21},
            {"name": "untrusted", "ipv4_network": "10.0.14.0/24"},
        ],
    }


def named_network(networking_dict: dict[str, Any], name: str) -> dict[str, Any]:
    """
    Returns the configuration of the network with a given name.
    """
    networks: list[dict[str, Any]] = networking_dict["networks"]
    return next(n for n in networks if n["name"] == name)


ENCRYPTED_PASSWORD = "$5$testsalt$" + "a" * 43


@pytest.fixture
def admin_dict() -> dict[str, Any]:
    return {
        "username": "admin",
        "full_name": "Test Admin",
        "encrypted_password": ENCRYPTED_PASSWORD,
        "pubkey": "ssh-ed25519 AAAAtest",
    }


@pytest.fixture
def router_dict(admin_dict: dict[str, Any]) -> dict[str, Any]:
    return {
        "admin": admin_dict,
        "pppoe": {"username": "pppoe-user", "password": "pppoe-secret"},
        "dyndns": {
            "hostname": "dyndns.example.com",
            "url": "https://dyndns.example.com/",
            "username": "dyndns-user",
            "password": "dyndns-secret",
        },
    }


@pytest.fixture
def port_forward_dict() -> dict[str, Any]:
    return {
        "description": "https",
        "src_port": 443,
        "dest_ip": "10.0.2.10",
        "dest_port": 8443,
        "protocol": "tcp",
    }


def second_assignment(**overrides: str) -> dict[str, Any]:
    """
    Returns an assignment that conflicts with assignment_dict only in overrides.
    """
    return {
        "name": "host-b",
        "mac": "00:00:5e:00:53:02",
        "ip": "10.0.12.6",
        **overrides,
    }


class TestHomelabDHCPRange:
    """
    Container for HomelabDHCPRange tests.
    """

    def test_allows_a_single_address(self) -> None:
        """
        Tests that a range may start and end on the same address.
        """
        address = IPv4Address("10.0.12.10")

        dhcp_range = HomelabDHCPRange(address, address)

        assert dhcp_range.start == dhcp_range.end == address

    def test_rejects_end_before_start(self) -> None:
        """
        Tests that a range must not end before it starts.
        """
        with pytest.raises(InvalidConfigurationError, match="is before"):
            HomelabDHCPRange(IPv4Address("10.0.12.20"), IPv4Address("10.0.12.10"))


class TestHomelabDHCPAssignment:
    """
    Container for HomelabDHCPAssignment tests.
    """

    def test_from_dict_parses_values(self, assignment_dict: dict[str, Any]) -> None:
        """
        Tests that from_dict() parses values and normalizes the MAC to lowercase.
        """
        assignment = HomelabDHCPAssignment.from_dict(assignment_dict)

        assert assignment.name == "host-a"
        assert assignment.mac == "00:00:5e:00:53:01"
        assert assignment.ip == IPv4Address("10.0.12.5")
        assert assignment.dns == ["host-a.lan"]

    def test_dns_is_optional(self, assignment_dict: dict[str, Any]) -> None:
        """
        Tests that an assignment does not need DNS names.
        """
        del assignment_dict["dns"]

        assert HomelabDHCPAssignment.from_dict(assignment_dict).dns == []

    @pytest.mark.parametrize(
        "mac",
        [
            "not-a-mac",
            "00:00:5e:00:53",
            "00:00:5e:00:53:01:02",
            "00-00-5e-00-53-01",
            "00:00:5e:00:53:0g",
            "00:00:5e:00:53:01\n",
            None,
        ],
    )
    def test_rejects_invalid_macs(
        self, assignment_dict: dict[str, Any], mac: Any
    ) -> None:
        """
        Tests that MACs must be strings of the expected format.
        """
        assignment_dict["mac"] = mac

        with pytest.raises(InvalidConfigurationError, match="not a MAC address"):
            HomelabDHCPAssignment.from_dict(assignment_dict)

    def test_rejects_unquoted_decimal_mac(self) -> None:
        """
        Tests that a MAC that YAML reads as a base 60 integer gets a clear error.
        """
        parsed = yaml_safe_load("{name: host, mac: 11:22:33:44:55:56, ip: 10.0.12.5}")
        assert isinstance(parsed["mac"], int)

        with pytest.raises(InvalidConfigurationError, match="must be quoted"):
            HomelabDHCPAssignment.from_dict(parsed)

    def test_rejects_dns_string(self, assignment_dict: dict[str, Any]) -> None:
        """
        Tests that a bare string is not treated as a list of names.
        """
        assignment_dict["dns"] = "host-a.lan"

        with pytest.raises(InvalidConfigurationError, match="dns must be a list"):
            HomelabDHCPAssignment.from_dict(assignment_dict)

    @pytest.mark.parametrize("key", ["name", "mac", "ip"])
    def test_from_dict_rejects_missing_keys(
        self, assignment_dict: dict[str, Any], key: str
    ) -> None:
        """
        Tests that from_dict() names a missing key.
        """
        del assignment_dict[key]

        with pytest.raises(InvalidConfigurationError, match=f"missing '{key}'"):
            HomelabDHCPAssignment.from_dict(assignment_dict)


class TestHomelabDHCP:
    """
    Container for HomelabDHCP tests.
    """

    def test_range_and_assignments_are_optional(self) -> None:
        """
        Tests that an empty DHCP configuration has no range and no assignments.
        """
        dhcp = HomelabDHCP.from_dict({})

        assert dhcp.range is None
        assert dhcp.assignments == []


class TestHomelabNetwork:
    """
    Container for HomelabNetwork tests.
    """

    def test_from_dict_parses_values(self, network_dict: dict[str, Any]) -> None:
        """
        Tests that from_dict() parses the network and its nested DHCP configuration.
        """
        network = HomelabNetwork.from_dict(network_dict)

        assert network.name == "trusted"
        assert network.ipv4_network == IPv4Network("10.0.12.0/23")
        assert network.vlan_id == 12
        assert network.dhcp is not None
        assert network.dhcp.range is not None
        assert network.dhcp.range.start == IPv4Address("10.0.12.10")
        assert network.dhcp.range.end == IPv4Address("10.0.12.250")
        assert [a.name for a in network.dhcp.assignments] == ["host-a"]

    def test_vlan_and_dhcp_are_optional(self) -> None:
        """
        Tests that a network only needs a name and a subnet.
        """
        network = HomelabNetwork.from_dict(
            {"name": "modem", "ipv4_network": "10.0.1.0/24"}
        )

        assert network.vlan_id is None
        assert network.dhcp is None

    @pytest.mark.parametrize(
        "subnet,interface",
        [
            ("10.0.12.0/23", "10.0.12.1/23"),
            ("10.0.1.0/31", "10.0.1.0/31"),
            ("10.0.1.7/32", "10.0.1.7/32"),
        ],
    )
    def test_router_interface_uses_first_host(
        self, subnet: str, interface: str
    ) -> None:
        """
        Tests that the router takes the first host, whatever the prefix length.
        """
        network = HomelabNetwork("test", IPv4Network(subnet))

        assert network.router_interface == IPv4Interface(interface)

    @pytest.mark.parametrize("vlan_id", [1, 4094])
    def test_allows_vlan_id_limits(self, vlan_id: int) -> None:
        """
        Tests the lowest and highest usable VLAN IDs.
        """
        network = HomelabNetwork("test", IPv4Network("10.0.1.0/24"), vlan_id)

        assert network.vlan_id == vlan_id

    @pytest.mark.parametrize("vlan_id", [0, 4095, -1, "12", True])
    def test_rejects_invalid_vlan_ids(
        self, network_dict: dict[str, Any], vlan_id: Any
    ) -> None:
        """
        Tests that VLAN IDs must be integers from 1 to 4094.
        """
        network_dict["vlan_id"] = vlan_id

        with pytest.raises(InvalidConfigurationError, match="'trusted': VLAN ID"):
            HomelabNetwork.from_dict(network_dict)

    @pytest.mark.parametrize(
        "subnet",
        [
            "not-a-network",
            # Host bits are set, which is most likely a typo.
            "10.0.12.1/23",
        ],
    )
    def test_rejects_invalid_subnets(
        self, network_dict: dict[str, Any], subnet: str
    ) -> None:
        """
        Tests that subnets must parse, and must not have host bits set.
        """
        network_dict["ipv4_network"] = subnet

        with pytest.raises(InvalidConfigurationError, match="network 'trusted'"):
            HomelabNetwork.from_dict(network_dict)

    def test_rejects_missing_subnet(self) -> None:
        """
        Tests that a network must have a subnet.
        """
        with pytest.raises(
            InvalidConfigurationError, match="'trusted': missing 'ipv4_network'"
        ):
            HomelabNetwork.from_dict({"name": "trusted"})

    def test_names_network_when_nested_value_is_invalid(
        self, network_dict: dict[str, Any], assignment_dict: dict[str, Any]
    ) -> None:
        """
        Tests that errors from nested configuration say which network they are in.
        """
        assignment_dict["ip"] = "10.0.12.256"

        with pytest.raises(
            InvalidConfigurationError, match="network 'trusted'.*10.0.12.256"
        ):
            HomelabNetwork.from_dict(network_dict)

    def test_names_network_when_range_is_reversed(
        self, network_dict: dict[str, Any]
    ) -> None:
        """
        Tests that a reversed DHCP range says which network it is in.
        """
        network_dict["dhcp"]["range"] = {"start": "10.0.12.20", "end": "10.0.12.10"}

        with pytest.raises(
            InvalidConfigurationError, match="network 'trusted'.*is before"
        ):
            HomelabNetwork.from_dict(network_dict)

    @pytest.mark.parametrize(
        "bound,start,end",
        [
            ("start", "10.0.11.10", "10.0.12.250"),
            ("end", "10.0.12.10", "10.0.14.250"),
        ],
    )
    def test_rejects_range_outside_subnet(
        self, network_dict: dict[str, Any], bound: str, start: str, end: str
    ) -> None:
        """
        Tests that both DHCP range bounds must fall inside the subnet.
        """
        network_dict["dhcp"]["range"] = {"start": start, "end": end}

        with pytest.raises(
            InvalidConfigurationError,
            match=f"'trusted': DHCP range {bound} address .* is not in 10.0.12.0/23",
        ):
            HomelabNetwork.from_dict(network_dict)

    def test_rejects_assignment_outside_subnet(
        self, network_dict: dict[str, Any], assignment_dict: dict[str, Any]
    ) -> None:
        """
        Tests that assignment IPs must fall inside the subnet.
        """
        assignment_dict["ip"] = "10.0.20.5"

        with pytest.raises(
            InvalidConfigurationError,
            match="'trusted': host-a address 10.0.20.5 is not in 10.0.12.0/23",
        ):
            HomelabNetwork.from_dict(network_dict)

    @pytest.mark.parametrize(
        "overrides,field",
        [
            ({"name": "host-a"}, "name"),
            # Differs in case only, so this is only a duplicate after normalizing.
            ({"mac": "00:00:5e:00:53:01"}, "MAC"),
            ({"ip": "10.0.12.5"}, "IP"),
        ],
    )
    def test_rejects_duplicate_assignments(
        self, network_dict: dict[str, Any], overrides: dict[str, str], field: str
    ) -> None:
        """
        Tests that names, MACs and IPs must be unique among a network's assignments.
        """
        network_dict["dhcp"]["assignments"].append(second_assignment(**overrides))

        with pytest.raises(
            InvalidConfigurationError,
            match=f"'trusted': duplicate DHCP assignment {field}",
        ):
            HomelabNetwork.from_dict(network_dict)


class TestHomelabDNSRecord:
    """
    Container for HomelabDNSRecord tests.
    """

    def test_from_dict_parses_values(self) -> None:
        """
        Tests that from_dict() parses every field.
        """
        record = HomelabDNSRecord.from_dict(
            {"name": "host", "ip": "10.0.2.10", "dns": ["host.lan"]}
        )

        assert record == HomelabDNSRecord(
            "host", IPv4Address("10.0.2.10"), ["host.lan"]
        )

    def test_rejects_dns_string(self) -> None:
        """
        Tests that a bare string is not treated as a list of names.
        """
        with pytest.raises(InvalidConfigurationError, match="dns must be a list"):
            HomelabDNSRecord.from_dict(
                {"name": "host", "ip": "10.0.2.10", "dns": "host.lan"}
            )

    def test_rejects_invalid_address(self) -> None:
        """
        Tests that the address must parse.
        """
        with pytest.raises(InvalidConfigurationError, match="invalid DNS record"):
            HomelabDNSRecord.from_dict({"name": "host", "ip": "nope", "dns": []})


class TestHomelabPortForward:
    """
    Container for HomelabPortForward tests.
    """

    def test_from_dict_parses_values(self, port_forward_dict: dict[str, Any]) -> None:
        """
        Tests that from_dict() parses every field.
        """
        forward = HomelabPortForward.from_dict(port_forward_dict)

        assert forward == HomelabPortForward(
            "https", 443, IPv4Address("10.0.2.10"), 8443, "tcp"
        )

    @pytest.mark.parametrize("key", ["src_port", "dest_port"])
    @pytest.mark.parametrize("port", [0, 65536, "443", True])
    def test_rejects_invalid_ports(
        self, port_forward_dict: dict[str, Any], key: str, port: Any
    ) -> None:
        """
        Tests that ports must be integers from 1 to 65535.
        """
        port_forward_dict[key] = port

        with pytest.raises(InvalidConfigurationError, match="'https': port must be"):
            HomelabPortForward.from_dict(port_forward_dict)

    @pytest.mark.parametrize("protocol", ["tcp", "udp", "tcp_udp"])
    def test_allows_protocols(
        self, port_forward_dict: dict[str, Any], protocol: str
    ) -> None:
        """
        Tests each protocol the router supports.
        """
        port_forward_dict["protocol"] = protocol

        assert HomelabPortForward.from_dict(port_forward_dict).protocol == protocol

    def test_rejects_invalid_protocol(self, port_forward_dict: dict[str, Any]) -> None:
        """
        Tests that the protocol must be one the router supports.
        """
        port_forward_dict["protocol"] = "icmp"

        with pytest.raises(InvalidConfigurationError, match="protocol must be"):
            HomelabPortForward.from_dict(port_forward_dict)

    def test_from_dict_rejects_missing_keys(
        self, port_forward_dict: dict[str, Any]
    ) -> None:
        """
        Tests that from_dict() names a missing key.
        """
        del port_forward_dict["dest_ip"]

        with pytest.raises(InvalidConfigurationError, match="missing 'dest_ip'"):
            HomelabPortForward.from_dict(port_forward_dict)


class TestHomelabRouterAdmin:
    """
    Container for HomelabRouterAdmin tests.
    """

    def test_splits_pubkey(self, admin_dict: dict[str, Any]) -> None:
        """
        Tests that the public key's parts are available separately.
        """
        admin = HomelabRouterAdmin.from_dict(admin_dict)

        assert admin.pubkey_type == "ssh-ed25519"
        assert admin.pubkey_key == "AAAAtest"

    @pytest.mark.parametrize(
        "encrypted_password",
        [
            "plaintext",
            # The router does not support specifying rounds.
            "$5$rounds=12345$testsalt$" + "a" * 43,
            # A SHA-512 hash, not SHA-256.
            "$6$testsalt$" + "a" * 86,
            None,
        ],
    )
    def test_rejects_invalid_hash_without_revealing_it(
        self, admin_dict: dict[str, Any], encrypted_password: Any
    ) -> None:
        """
        Tests that the hash must suit the router, and is left out of the error.
        """
        admin_dict["encrypted_password"] = encrypted_password

        with pytest.raises(
            InvalidConfigurationError, match="sha256_crypt hash"
        ) as excinfo:
            HomelabRouterAdmin.from_dict(admin_dict)

        assert str(encrypted_password) not in str(excinfo.value)

    @pytest.mark.parametrize(
        "pubkey", ["ssh-ed25519", "ssh-ed25519 AAAAtest me@host", None]
    )
    def test_rejects_invalid_pubkey(
        self, admin_dict: dict[str, Any], pubkey: Any
    ) -> None:
        """
        Tests that the public key must have exactly a type and a key.
        """
        admin_dict["pubkey"] = pubkey

        with pytest.raises(InvalidConfigurationError, match="pubkey must be"):
            HomelabRouterAdmin.from_dict(admin_dict)


class TestHomelabRouter:
    """
    Container for HomelabRouter tests.
    """

    def test_from_dict_parses_values(self, router_dict: dict[str, Any]) -> None:
        """
        Tests that from_dict() parses each section.
        """
        router = HomelabRouter.from_dict(router_dict)

        assert router.admin.username == "admin"
        assert router.pppoe == HomelabPPPoE("pppoe-user", "pppoe-secret")
        assert router.dyndns.hostname == "dyndns.example.com"

    def test_repr_hides_credentials(self, router_dict: dict[str, Any]) -> None:
        """
        Tests that credentials do not appear in debug output.
        """
        text = repr(HomelabRouter.from_dict(router_dict))

        assert "pppoe-user" in text
        assert "pppoe-secret" not in text
        assert "dyndns-secret" not in text
        assert ENCRYPTED_PASSWORD not in text

    @pytest.mark.parametrize("password", ["", None, 12345])
    def test_rejects_invalid_passwords(self, password: Any) -> None:
        """
        Tests that passwords must be non-empty strings, and stay out of the error.
        """
        with pytest.raises(
            InvalidConfigurationError, match="password must be a non-empty string"
        ):
            HomelabPPPoE("user", password)

        with pytest.raises(
            InvalidConfigurationError, match="password must be a non-empty string"
        ):
            HomelabDynDNS("host", "https://example.com/", "user", password)

    @pytest.mark.parametrize("key", ["admin", "pppoe", "dyndns"])
    def test_from_dict_rejects_missing_sections(
        self, router_dict: dict[str, Any], key: str
    ) -> None:
        """
        Tests that from_dict() names a missing section.
        """
        del router_dict[key]

        with pytest.raises(InvalidConfigurationError, match=f"missing '{key}'"):
            HomelabRouter.from_dict(router_dict)

    @pytest.mark.parametrize(
        "section,key,cls",
        [
            ("admin", "username", HomelabRouterAdmin),
            ("pppoe", "password", HomelabPPPoE),
            ("dyndns", "url", HomelabDynDNS),
        ],
    )
    def test_from_dict_rejects_missing_keys(
        self, router_dict: dict[str, Any], section: str, key: str, cls: Any
    ) -> None:
        """
        Tests that each section names a missing key.
        """
        del router_dict[section][key]

        with pytest.raises(InvalidConfigurationError, match=f"missing '{key}'"):
            cls.from_dict(router_dict[section])


class TestHomelabSwitchPort:
    """
    Container for HomelabSwitchPort tests.
    """

    def test_from_dict_parses_values(self) -> None:
        """
        Tests that from_dict() parses every field.
        """
        port = HomelabSwitchPort.from_dict(
            {
                "port": "0/1",
                "description": "router uplink",
                "untagged": "trusted",
                "tagged": ["infra"],
            }
        )

        assert port == HomelabSwitchPort("0/1", "trusted", ["infra"], "router uplink")

    def test_from_dict_accepts_bare_port_number(self) -> None:
        """
        Tests that a port number YAML reads as an integer is kept as a string.
        """
        assert (
            HomelabSwitchPort.from_dict({"port": 1, "untagged": "trusted"}).port == "1"
        )

    def test_may_carry_only_tagged_networks(self) -> None:
        """
        Tests that a port does not need an untagged network.
        """
        port = HomelabSwitchPort.from_dict({"port": "0/1", "tagged": ["infra"]})

        assert port.untagged is None

    def test_rejects_port_without_networks(self) -> None:
        """
        Tests that a port must carry at least one network.
        """
        with pytest.raises(InvalidConfigurationError, match="carries no networks"):
            HomelabSwitchPort("0/1")

    def test_rejects_tagged_string(self) -> None:
        """
        Tests that a bare string is not treated as a list of names.
        """
        with pytest.raises(InvalidConfigurationError, match="tagged must be a list"):
            HomelabSwitchPort.from_dict({"port": "0/1", "tagged": "infra"})

    def test_rejects_duplicate_tagged_networks(self) -> None:
        """
        Tests that a port does not list a tagged network twice.
        """
        with pytest.raises(InvalidConfigurationError, match="duplicate tagged"):
            HomelabSwitchPort("0/1", tagged=["infra", "infra"])

    def test_from_dict_rejects_missing_port(self) -> None:
        """
        Tests that from_dict() names a missing port.
        """
        with pytest.raises(InvalidConfigurationError, match="missing 'port'"):
            HomelabSwitchPort.from_dict({"untagged": "trusted"})


class TestHomelabSwitch:
    """
    Container for HomelabSwitch tests.
    """

    def test_ports_are_optional(self) -> None:
        """
        Tests that a switch may have no managed ports.
        """
        assert HomelabSwitch.from_dict({"name": "core"}).ports == []

    def test_rejects_duplicate_ports(self) -> None:
        """
        Tests that a port is only configured once.
        """
        port = {"port": "0/1", "untagged": "trusted"}

        with pytest.raises(InvalidConfigurationError, match="duplicate port: 0/1"):
            HomelabSwitch.from_dict({"name": "core", "ports": [port, port]})

    def test_from_dict_rejects_missing_name(self) -> None:
        """
        Tests that from_dict() names a missing name.
        """
        with pytest.raises(InvalidConfigurationError, match="missing 'name'"):
            HomelabSwitch.from_dict({})


class TestHomelabNetworks:
    """
    Container for HomelabNetworks tests.
    """

    @pytest.mark.parametrize("key", NETWORK_ATTRIBUTES)
    def test_from_dict_rejects_missing_networks(
        self, networking_dict: dict[str, Any], key: str
    ) -> None:
        """
        Tests that every network is required, and that a missing one is named.
        """
        networking_dict["networks"].remove(named_network(networking_dict, key))

        with pytest.raises(InvalidConfigurationError, match=f"missing '{key}'"):
            HomelabNetworks.from_list(networking_dict["networks"])

    def test_from_dict_rejects_invalid_network(
        self, networking_dict: dict[str, Any]
    ) -> None:
        """
        Tests that a network with no configuration raises the expected error.
        """
        networking_dict["networks"][0] = None

        with pytest.raises(InvalidConfigurationError, match="homelab network"):
            HomelabNetworks.from_list(networking_dict["networks"])


class TestHomelabNetworksList:
    """
    Container for tests of how HomelabNetworks reads its list.
    """

    def test_rejects_missing_name(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that every network must have a name.
        """
        del named_network(networking_dict, "modem")["name"]

        with pytest.raises(InvalidConfigurationError, match="missing 'name'"):
            HomelabNetworks.from_list(networking_dict["networks"])

    def test_rejects_duplicate_networks(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that a network can't be listed twice.
        """
        networking_dict["networks"].append(named_network(networking_dict, "modem"))

        with pytest.raises(InvalidConfigurationError, match="duplicate network: modem"):
            HomelabNetworks.from_list(networking_dict["networks"])

    def test_rejects_unknown_networks(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that a misspelled network is not silently ignored.
        """
        networking_dict["networks"].append(
            {"name": "nope", "ipv4_network": "10.0.30.0/24"}
        )

        with pytest.raises(InvalidConfigurationError, match="unknown network: nope"):
            HomelabNetworks.from_list(networking_dict["networks"])

    def test_rejects_map(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that the previous shape, a map of networks, gets a clear error.
        """
        networking_dict["networks"] = {"modem": {"ipv4_network": "10.0.1.0/24"}}

        with pytest.raises(InvalidConfigurationError, match="homelab network"):
            HomelabNetworks.from_list(networking_dict["networks"])


class TestHomelabNetworkingSwitches:
    """
    Container for tests of switches in HomelabNetworking.
    """

    @staticmethod
    def with_port(networking_dict: dict[str, Any], **port: Any) -> dict[str, Any]:
        """
        Returns the networking configuration with a switch that has one port.
        """
        networking_dict["switches"] = [
            {"name": "core", "ports": [{"port": "0/1", **port}]}
        ]
        return networking_dict

    def test_switches_are_optional(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that the configuration does not need any switches.
        """
        assert HomelabNetworking.from_dict(networking_dict).switches == []

    def test_networks_are_keyed_by_name(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that the networks property holds every network.
        """
        networks = HomelabNetworking.from_dict(networking_dict).networks.by_name

        assert sorted(networks) == sorted(NETWORK_ATTRIBUTES)

    def test_parses_switch_port(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that a port may carry an untagged and a tagged network.
        """
        named_network(networking_dict, "infra")["vlan_id"] = 20
        networking = HomelabNetworking.from_dict(
            self.with_port(networking_dict, untagged="trusted", tagged=["infra"])
        )

        assert networking.switches[0].ports[0].tagged == ["infra"]

    def test_allows_untagged_network_without_vlan(
        self, networking_dict: dict[str, Any]
    ) -> None:
        """
        Tests that a network that has not moved onto a VLAN can be carried untagged.
        """
        networking = HomelabNetworking.from_dict(
            self.with_port(networking_dict, untagged="modem")
        )

        assert networking.switches[0].ports[0].untagged == "modem"

    @pytest.mark.parametrize(
        "port",
        [{"untagged": "nonexistent"}, {"tagged": ["nonexistent"]}],
    )
    def test_rejects_unknown_networks(
        self, networking_dict: dict[str, Any], port: dict[str, Any]
    ) -> None:
        """
        Tests that ports must refer to networks that exist.
        """
        with pytest.raises(
            InvalidConfigurationError,
            match="'core' port '0/1': no network 'nonexistent'",
        ):
            HomelabNetworking.from_dict(self.with_port(networking_dict, **port))

    def test_rejects_tagged_network_without_vlan(
        self, networking_dict: dict[str, Any]
    ) -> None:
        """
        Tests that a network can only be tagged if it has a VLAN ID.
        """
        with pytest.raises(InvalidConfigurationError, match="must have a VLAN ID"):
            HomelabNetworking.from_dict(
                self.with_port(networking_dict, tagged=["modem"])
            )

    def test_rejects_vlan_both_tagged_and_untagged(
        self, networking_dict: dict[str, Any]
    ) -> None:
        """
        Tests that networks sharing a VLAN ID can't be both tagged and untagged.
        """
        named_network(networking_dict, "infra")["vlan_id"] = 12

        with pytest.raises(
            InvalidConfigurationError, match="VLAN 12 is both tagged and untagged"
        ):
            HomelabNetworking.from_dict(
                self.with_port(networking_dict, untagged="trusted", tagged=["infra"])
            )

    def test_parses_dns_records_and_port_forwards(
        self, networking_dict: dict[str, Any], port_forward_dict: dict[str, Any]
    ) -> None:
        """
        Tests that DNS records and port forwards are parsed, and are optional.
        """
        assert HomelabNetworking.from_dict(networking_dict).dns_records == []

        networking_dict["dns_records"] = [
            {"name": "host", "ip": "10.0.2.10", "dns": ["host.lan"]}
        ]
        networking_dict["port_forwards"] = [port_forward_dict]
        networking = HomelabNetworking.from_dict(networking_dict)

        assert networking.dns_records[0].name == "host"
        assert networking.port_forwards[0].dest_port == 8443

    def test_rejects_duplicate_dns_records(
        self, networking_dict: dict[str, Any]
    ) -> None:
        """
        Tests that DNS record names must be unique.
        """
        record = {"name": "host", "ip": "10.0.2.10", "dns": []}
        networking_dict["dns_records"] = [record, record]

        with pytest.raises(InvalidConfigurationError, match="duplicate DNS record"):
            HomelabNetworking.from_dict(networking_dict)

    def test_rejects_duplicate_switches(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that switch names must be unique.
        """
        networking_dict["switches"] = [{"name": "core"}, {"name": "core"}]

        with pytest.raises(InvalidConfigurationError, match="duplicate switch: core"):
            HomelabNetworking.from_dict(networking_dict)


class TestHomelabNetworking:
    """
    Container for HomelabNetworking tests.
    """

    def test_from_dict_parses_every_network(
        self, networking_dict: dict[str, Any]
    ) -> None:
        """
        Tests that from_dict() assigns each network to its attribute, named by its key.
        """
        networking = HomelabNetworking.from_dict(networking_dict)

        assert networking.upstream_dns == [
            IPv4Address("192.0.2.53"),
            IPv4Address("198.51.100.53"),
        ]
        networks = {
            attribute: getattr(networking.networks, attribute)
            for attribute in NETWORK_ATTRIBUTES
        }
        for attribute, network in networks.items():
            assert network.name == attribute
            assert network.ipv4_network == IPv4Network(
                named_network(networking_dict, attribute)["ipv4_network"]
            )
        assert networking.networks.modem.router_interface == IPv4Interface(
            "10.0.1.1/24"
        )

    def test_allows_shared_vlan_ids_and_overlapping_networks(
        self, networking_dict: dict[str, Any]
    ) -> None:
        """
        Tests that networks may share a VLAN ID, and may overlap.
        """
        named_network(networking_dict, "untrusted")["vlan_id"] = 12
        named_network(networking_dict, "untrusted")["ipv4_network"] = "10.0.13.0/24"

        networking = HomelabNetworking.from_dict(networking_dict)

        assert (
            networking.networks.trusted.vlan_id
            == networking.networks.untrusted.vlan_id
            == 12
        )
        assert networking.networks.untrusted.ipv4_network.subnet_of(
            networking.networks.trusted.ipv4_network
        )

    def test_from_dict_provides_named_ports(
        self, networking_dict: dict[str, Any]
    ) -> None:
        """
        Tests that from_dict() provides the well-known ports, by name.
        """
        networking = HomelabNetworking.from_dict(networking_dict)

        assert networking.ports == HomelabPorts()
        assert networking.ports.dns == 53
        assert networking.ports.https == 443

    @pytest.mark.parametrize(
        "key,value",
        [
            ("upstream_dns", ["not-an-address"]),
            ("upstream_dns", 53),
            ("networks", None),
        ],
    )
    def test_from_dict_rejects_invalid_values(
        self, networking_dict: dict[str, Any], key: str, value: Any
    ) -> None:
        """
        Tests that from_dict() raises InvalidConfigurationError for bad values.
        """
        networking_dict[key] = value

        with pytest.raises(InvalidConfigurationError, match="homelab networking"):
            HomelabNetworking.from_dict(networking_dict)

    @pytest.mark.parametrize("key", ["upstream_dns", "networks", "router"])
    def test_from_dict_rejects_missing_keys(
        self, networking_dict: dict[str, Any], key: str
    ) -> None:
        """
        Tests that from_dict() names a missing key.
        """
        del networking_dict[key]

        with pytest.raises(InvalidConfigurationError, match=f"missing '{key}'"):
            HomelabNetworking.from_dict(networking_dict)


class TestHomelab:
    """
    Container for Homelab tests.
    """

    def test_from_dict_parses_network(self, networking_dict: dict[str, Any]) -> None:
        """
        Tests that from_dict() parses the nested configuration.
        """
        homelab = Homelab.from_dict(
            {"kubernetes_context": "k8stest", "network": networking_dict}
        )

        assert homelab.kubernetes_context == "k8stest"
        assert homelab.network.networks.modem.ipv4_network == IPv4Network("10.0.1.0/24")
        assert homelab.network.router.pppoe.username == "pppoe-user"

    def test_dummy_configuration_names_networks_after_attributes(self) -> None:
        """
        Tests that dummy networks use the same names that from_dict() would give them.
        """
        networks = dummy_infrastructure_configuration().homelab.network.networks

        for attribute in NETWORK_ATTRIBUTES:
            assert getattr(networks, attribute).name == attribute
