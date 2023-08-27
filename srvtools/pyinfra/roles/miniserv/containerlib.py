"""
roles/miniserv/containerlib
---------------------------

This module provides container helpers for the miniserv role.
"""

from ipaddress import ip_network, IPv4Network
from os import path
from typing import Callable, List, Mapping, Optional, TypeVar

from lib.model.container import Container, ContainerNetwork, Volume
from lib.pyinfra import Pyinfra

from .vars import data_dir

T = TypeVar("T", bound="MiniservContainer")


class _SwagNetworkManager:
    """
    Provides named container networks for web applications that are
    proxied by the Secure Web Application Gateway container (SWAG).

    It tracks which networks are provided, so that we don't need to
    repeat them when we configure the SWAG container.
    """

    def __init__(self) -> None:
        # Each network requires three usable addresses:
        # * One for the network gateway
        # * One of the container that SWAG is proxying for
        # * One for SWAG itself
        #
        # A /29 is the smallest prefix we can allocate to get three usable addresses.
        self._network_alloc = ip_network("169.254.169.0/24").subnets(new_prefix=29)
        self.swag_networks: List[ContainerNetwork] = list()
        self._new_networks = True

    def close(self) -> None:
        self._new_networks = False

    def network(self, name: str) -> ContainerNetwork:
        if not self._new_networks:
            raise Exception("can't create new network after close")
        alloc_subnet = next(self._network_alloc)
        assert isinstance(alloc_subnet, IPv4Network)
        net = ContainerNetwork(f"swag-{name}", alloc_subnet)
        self.swag_networks.append(net)
        return net


class MiniservContainer(Container):
    def __init__(
        self: T,
        name: str,
        image: str,
        get_environment: Callable[[], Mapping[str, str]],
        deploy_config: Optional[Callable[[Pyinfra, T], bool]],
        volumes: List[Volume],
        networks: List[ContainerNetwork],
        ports: List[str],
        uid: Optional[int],
        gid: Optional[int],
        restart: str,
        max_restarts: int,
        restart_sec: int,
    ) -> None:
        super().__init__(
            name=name,
            image=image,
            get_environment=get_environment,
            deploy_config=deploy_config,
            volumes=volumes,
            networks=networks,
            ports=ports,
            uid=uid,
            gid=gid,
            restart=restart,
            max_restarts=max_restarts,
            restart_sec=restart_sec,
        )
        for v in volumes:
            if not path.isabs(v.src):
                v.src = path.join(self.data_dir, v.src)

    @property
    def data_dir(self) -> str:
        return path.join(data_dir, self.name)


_swag_network_manager = _SwagNetworkManager()


def swag_networks() -> List[ContainerNetwork]:
    _swag_network_manager.close()
    return _swag_network_manager.swag_networks


def web_networks(name: str) -> List[ContainerNetwork]:
    return [_swag_network_manager.network(name)]
