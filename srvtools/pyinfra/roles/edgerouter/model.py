"""
roles/edgerouter/model
----------------------

This module contains object models used in this role.
"""

from itertools import chain
from typing import Any, Dict, List, Iterable, Iterator, Set

from passlib.hash import sha256_crypt


class CenturyLink:
    """
    Represents required CenturyLink configuration.
    """
    def __init__(self, pppoe_username: str, pppoe_password: str) -> None:
        self.pppoe_username = pppoe_username
        self.pppoe_password = pppoe_password

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CenturyLink":
        return cls(d["pppoe_username"], d["pppoe_password"])


class DNS:
    """
    Represents one or more DNS entries pointing at an IP address.
    """
    def __init__(self, name: str, ip: str, dns: List[str]) -> None:
        self.name = name
        self.ip = ip
        self.dns = dns

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.ip}, {self.dns})"

    @classmethod
    def from_dict(cls, name: str, d: Dict[str, Any]) -> "DNS":
        return cls(name, d["ip"], d["dns"])


class DynDNSConfig:
    """
    Represents a dynamic DNS configuration.
    """
    def __init__(self, hostname: str, url: str, username: str, password: str) -> None:
        self.hostname = hostname
        self.url = url
        self.username = username
        self.password = password

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.hostname})"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DynDNSConfig":
        return cls(d["hostname"], d["url"], d["username"], d["password"])


class PortForward:
    """
    Represents a router port forward.
    """
    def __init__(self, description: str, dest_ip: str, src_port: int, dest_port: int, protocol: str) -> None:
        self.description = description
        self.dest_ip = dest_ip
        self.src_port = src_port
        self.dest_port = dest_port
        self.protocol = protocol

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.dest_ip}: {self.src_port} -> {self.dest_port})"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PortForward":
        return cls(d["description"], d["dest_ip"], d["src_port"], d["dest_port"], d["protocol"])


class StaticDHCP:
    """
    Represents a static DHCP entry.
    """
    def __init__(self, name: str, mac: str, ip: str, dns: List[str]) -> None:
        self.name = name
        self.mac = mac
        self.ip = ip
        self.dns = dns

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.ip})"

    @classmethod
    def from_dict(cls, name: str, d: Dict[str, Any]) -> "StaticDHCP":
        return cls(
            name=name,
            mac=d["mac"],
            ip=d["ip"],
            dns=d.get("dns", []),
        )


class StaticDHCPs:
    """
    An iterable collection of StaticDHCP objects.
    """
    def __init__(self, dhcps: Iterable[StaticDHCP]) -> None:
        self.dhcps = {d.name: d for d in dhcps}

    def __getitem__(self, k: str) -> StaticDHCP:
        return self.dhcps[k]

    def __iter__(self) -> Iterator[StaticDHCP]:
        return iter(self.dhcps.values())


class User:
    """
    Represents a router user configuration.
    """
    def __init__(self, username: str, full_name: str, password: str, hash_salt: str, pubkey: str) -> None:
        self.username = username
        self.password = password
        self.hash_salt = hash_salt
        self.pubkey = pubkey
        self.full_name = full_name

        self.pubkey_type, self.pubkey_key = self.pubkey.split(" ")

    def encrypted_password(self) -> str:
        """
        Returns the "encrypted password" for this user, suitable for passing
        to the `encrypted-password` field.
        """
        # Note: When a password hash uses something other than 5000 rounds, the "rounds"
        # must be returned as part of the hash. From the passlib documentation:
        #
        # >>> sha256_crypt.using(rounds=12345).hash("password")
        # '$5$rounds=12345$q3hvJE5mn5jKRsW.$BbbYTFiaImz9rTy03GGi.Jf9YY5bmxN0LU3p3uI1iUB'
        #
        # With rounds = 5000, the $rounds=...$ bit can be omitted completely. Also, it turns
        # out that the EdgeRouter being provisioned against here does not support specifying
        # the number of hash rounds. We have no choice but to use exactly 5000 rounds.
        #
        # See also:
        # https://passlib.readthedocs.io/en/stable/lib/passlib.hash.sha256_crypt.html
        implicit_rounds = 5000
        return sha256_crypt.using(salt=self.hash_salt, rounds=implicit_rounds).hash(self.password)


class WireguardPeer:
    """
    Represents a Wireguard peer.
    """
    def __init__(self, name: str, pubkey: str, ip: str, network_groups: List[str]) -> None:
        self.name = name
        self.pubkey = pubkey
        self.ip = ip
        self.network_groups = network_groups

    @classmethod
    def from_dict(cls, name: str, d: Dict[str, Any]) -> "WireguardPeer":
        return cls(
            name=name,
            pubkey=d["pubkey"],
            ip=d["ip"],
            network_groups=d.get("network_groups", []),
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.ip})"


class WireguardPeers:
    """
    An iterable collection of WireguardPeer objects.
    """
    def __init__(self, peers: Iterable[WireguardPeer]) -> None:
        self.peers = list(peers)

    def __getitem__(self, idx: int) -> WireguardPeer:
        return self.peers[idx]

    def __iter__(self) -> Iterator[WireguardPeer]:
        return iter(self.peers)

    def in_network_group(self, network_group: str) -> Iterable[WireguardPeer]:
        return filter(lambda p: network_group in p.network_groups, self.peers)

    def network_groups(self) -> Set[str]:
        """
        Returns all network groups referenced by Wireguard peers in this collection.
        """
        return set(chain.from_iterable(p.network_groups for p in self.peers))


class Host:
    """
    Represents a network host.
    """
    def __init__(self, name: str, ip: str, hostnames: List[str]) -> None:
        self.name = name
        self.ip = ip
        self.hostnames = hostnames

    @classmethod
    def from_dns(cls, d: DNS) -> "Host":
        return cls(d.name, d.ip, d.dns)

    @classmethod
    def from_static_dhcp(cls, d: StaticDHCP) -> "Host":
        return cls(d.name, d.ip, d.dns)
