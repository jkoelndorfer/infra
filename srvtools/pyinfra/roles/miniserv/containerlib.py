"""
roles/miniserv/containerlib
---------------------------

This module provides container helpers for the miniserv role.
"""

from ipaddress import ip_network, IPv4Network
from os import path
from typing import List

from lib.model.container import ContainerNetwork

from .vars import data_dir


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


_swag_network_manager = _SwagNetworkManager()


def container_data_dir(name: str) -> str:
    return path.join(data_dir, name)


def swag_networks() -> List[ContainerNetwork]:
    _swag_network_manager.close()
    return _swag_network_manager.swag_networks


def web_networks(name: str) -> List[ContainerNetwork]:
    return [_swag_network_manager.network(name)]
