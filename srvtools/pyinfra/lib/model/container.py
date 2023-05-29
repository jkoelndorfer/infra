"""
lib/model/container
-------------------

This module contains container object models.
"""

from ipaddress import IPv4Address, IPv4Network
from typing import Any, Callable, List, Mapping, Optional


class ContainerNetwork:
    def __init__(self, name: str, network: IPv4Network) -> None:
        self.name = name
        self.network = network

    @property
    def gateway_address(self) -> IPv4Address:
        # The gateway is the first address in the network, by convention.
        return next(self.network.hosts())

    @property
    def systemd_service_name(self) -> str:
        return f"docker-network-{self.name}.service"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {str(self.network)})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name and self.network == other.network


class Volume:
    def __init__(self, src: str, dest: str, mode: str = "rw") -> None:
        self.src = src
        self.dest = dest
        self.mode = mode


class Container:
    def __init__(
        self,
        name: str,
        image: str,
        get_environment: Callable[[], Mapping[str, str]],
        volumes: List[Volume],
        networks: List[ContainerNetwork],
        ports: List[str],
        uid: Optional[int],
        gid: Optional[int],
        restart: str,
        max_restarts: int,
        restart_sec: int,
    ) -> None:
        self.name = name
        self.image = image

        # Not all of the container's environment variables can be known at
        # build time, because the environment may contain secrets and we
        # don't want those persisted.
        #
        # Rather than specify the environment directly, the user should pass
        # a function that, when called at provision time, will return the
        # environment variables for the container.
        self.get_environment = get_environment

        self.volumes = volumes
        self.networks = networks
        self.restart = restart
        self.ports = ports

        # For "linuxserver" containers, uid/gid will be implicitly passed
        # via the environment as "PUID" and "PGID".
        self.uid = uid
        self.gid = gid

        # These fields only apply to containers managed by systemd.
        self.max_restarts = max_restarts
        self.restart_sec = restart_sec

    @classmethod
    def restarting(
        cls,
        name: str,
        image: str,
        get_environment: Callable[[], Mapping[str, str]],
        volumes: List[Volume],
        networks: List[ContainerNetwork],
        ports: List[str],
        uid: Optional[int],
        gid: Optional[int],
    ) -> "Container":
        """
        Creates a `Container` with some sensible defaults for restarting.
        """
        return cls(
            name, image, get_environment, volumes, networks,
            ports, uid, gid, restart="always", max_restarts=3, restart_sec=3,
        )
