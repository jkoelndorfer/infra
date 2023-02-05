"""
roles/miniserv/containerlib
---------------------------

This module provides container helpers for the miniserv role.
"""

from os import path
from typing import List

from .vars import data_dir


class _SwagNetworkManager:
    """
    Provides named container networks for web applications that are
    proxied by the Secure Web Application Gateway container (SWAG).

    It tracks which networks are provided, so that we don't need to
    repeat them when we configure the SWAG container.
    """
    def __init__(self) -> None:
        self.swag_networks: List[str] = list()
        self._new_networks = True

    def close(self) -> None:
        self._new_networks = False

    def network(self, name: str) -> str:
        if not self._new_networks:
            raise Exception("can't create new network after close")
        net = f"swag_{name}"
        self.swag_networks.append(net)
        return net


_swag_network_manager = _SwagNetworkManager()


def container_data_dir(name: str) -> str:
    return path.join(data_dir, name)


def swag_networks() -> List[str]:
    _swag_network_manager.close()
    return [
        "bridge",
        *_swag_network_manager.swag_networks,
    ]


def web_networks(name: str) -> List[str]:
    return [
        "bridge",
        _swag_network_manager.network(name),
    ]
