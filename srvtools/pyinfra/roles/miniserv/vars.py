"""
roles/miniserv/vars
-------------------

This module contains variables for the miniserv role.
"""

from collections import namedtuple

ContainerImages = namedtuple("ContainerImages", ["pihole", "swag", "syncthing", "unifi", "vaultwarden"])

container_images = ContainerImages(
    pihole="pihole/pihole:v5.8.1",
    swag="linuxserver/swag:1.31.0-ls155",
    syncthing="linuxserver/syncthing:v1.21.0-ls83",
    unifi="linuxserver/unifi-controller:7.3.76-ls174",
    vaultwarden="vaultwarden/server:1.27.0",
)
