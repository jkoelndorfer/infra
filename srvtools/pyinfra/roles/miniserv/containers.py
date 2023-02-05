"""
roles/miniserv/containers
-------------------------

This module defines the containers that run on miniserv.
"""

from os import path

from lib.model.container import Container, Volume as V
from lib.vars import home_router_ip, miniserv_domains, timezone
from .containerlib import container_data_dir, swag_networks, web_networks


def pihole_environment(ctr: Container):
    return {
        "TZ": timezone,
        "DNS1": home_router_ip,
        "DNS2": "no",
        "VIRTUAL_HOST": "pihole.johnk.io",
    }


pihole_container = Container(
    name="pihole",
    image="pihole/pihole:v5.8.1",
    get_environment=pihole_environment,
    volumes=[
        V("pi-hole", "/etc/pihole"),
        V("dnsmasq", "/etc/dnsmasq.d"),
    ],
    networks=web_networks("pihole"),
    ports=[
        "53:53/udp",
    ],
    uid=None,
    gid=None,
    restart="yes",
    max_restarts=3,
    restart_sec=5,
)


def syncthing_env(ctr: Container):
    return {}


def swag_environment(ctr: Container):
    url = "johnk.io"

    # SWAG expects a comma-separated list of only the host,
    # i.e. instead of "miniserv.johnk.io,pihole.johnk.io",
    # SWAG needs "miniserv,pihole".
    subdomains = ",".join(
        s.replace(f".{url}", "") for s in miniserv_domains
    )
    return {
        "URL": url,
        "SUBDOMAINS": subdomains,
        "ONLY_SUBDOMAINS": "true",
        "EMAIL": "letsencrypt@johnk.io",
        "VALIDATION": "http",  # TODO: Use DNS-based validation
        "STAGING": "false",
    }

swag_container = Container(
    name="swag",
    image="linuxserver/swag:1.31.0-ls155",
    get_environment=swag_environment,
    volumes=[
        V("config", "/config"),
        V(path.join(container_data_dir("vaultwarden"), "log"), "/vaultwarden-log", "ro"),
    ],
    ports=[
        "80:80/tcp",
        "443:443/tcp",
    ],
    networks=swag_networks(),
    restart="yes",
    max_restarts=3,
    restart_sec=5,
)

container_images = ContainerImages(
    pihole="pihole/pihole:v5.8.1",
    swag="linuxserver/swag:1.31.0-ls155",
    syncthing="linuxserver/syncthing:v1.21.0-ls83",
    unifi="linuxserver/unifi-controller:7.3.76-ls174",
    vaultwarden="vaultwarden/server:1.27.0",
)
