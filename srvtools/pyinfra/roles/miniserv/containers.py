"""
roles/miniserv/containers
-------------------------

This module defines the containers that run on miniserv.
"""

from os import path

from lib.model.container import Container, Volume as V
from lib.vars import dns_zone, home_router_ip, miniserv_domains, miniserv_domains_by_service, timezone
from .containerlib import container_data_dir, swag_networks, web_networks


def pihole_env():
    return {
        "TZ": timezone,
        "DNS1": home_router_ip,
        "DNS2": "no",
        "VIRTUAL_HOST": miniserv_domains_by_service["pihole"],
    }


pihole_container = Container.restarting(
    name="pihole",
    image="docker.io/pihole/pihole:v5.8.1",
    get_environment=pihole_env,
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
)


def syncthing_env():
    return {
        "TZ": timezone,
    }


syncthing_container = Container.restarting(
    name="syncthing",
    image="docker.io/linuxserver/syncthing:v1.21.0-ls83",
    get_environment=syncthing_env,
    volumes=[
        V("config", "/config"),
        V("data", "/data"),
    ],
    networks=web_networks("syncthing"),
    ports=[
        "22000:22000/tcp",
        "21027:21027/udp",
    ],
    uid=2000,
    gid=2000,
)


def unifi_env():
    return {
        "TZ": timezone,
    }


unifi_container = Container.restarting(
    name="unifi",
    image="docker.io/linuxserver/unifi-controller:7.3.76-ls174",
    get_environment=unifi_env,
    volumes=[
        V("config", "/config"),
    ],
    networks=web_networks("unifi"),
    ports=[
        "3478:3478/udp",
        "6789:6789/tcp",
        "8080:8080/tcp",
        "8081:8081/tcp",
        "10001:10001/udp",
    ],
    uid=2010,
    gid=2010,
)


def vaultwarden_env():
    vaultwarden_domain = miniserv_domains_by_service["vaultwarden"]
    return {
        "DOMAIN": f"https://{vaultwarden_domain}",
        "ROCKET_PORT": "8080",
        "SIGNUPS_ALLOWED": "false",
        "SHOW_PASSWORD_HINT": "false",
        "WEBSOCKET_ENABLED": "true",
        "EXTENDED_LOGGING": "true",
        "LOG_FILE": "/log/vaultwarden.log",

        "SMTP_HOST": "smtp.sendgrid.net",
        "SMTP_PORT": "587",
        "SMTP_SECURITY": "starttls",
        "SMTP_FROM": f"noreply@{vaultwarden_domain}",
        "SMTP_USERNAME": "apikey",
        "SMTP_PASSWORD": "TODO",
        "SMTP_AUTH_MECHANISM": "Login",
    }


vaultwarden_container = Container.restarting(
    name="vaultwarden",
    image="docker.io/vaultwarden/server:1.27.0",
    get_environment=vaultwarden_env,
    volumes=[
        V("data", "/data"),
        V("log", "/log"),
    ],
    networks=web_networks("vaultwarden"),
    ports=[],
    uid=2030,
    gid=2030,
)


def swag_environment():
    # SWAG expects a comma-separated list of only the host,
    # i.e. instead of "miniserv.johnk.io,pihole.johnk.io",
    # SWAG needs "miniserv,pihole".
    subdomains = ",".join(
        s.replace(f".{dns_zone}", "") for s in miniserv_domains
    )
    return {
        "URL": dns_zone,
        "SUBDOMAINS": subdomains,
        "ONLY_SUBDOMAINS": "true",
        "EMAIL": f"letsencrypt@{dns_zone}",
        "VALIDATION": "http",  # TODO: Use DNS-based validation
        "STAGING": "false",
    }

swag_container = Container.restarting(
    name="swag",
    image="docker.io/linuxserver/swag:1.31.0-ls155",
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
    uid=2020,
    gid=2020,
)

service_containers = [
    pihole_container,
    swag_container,
    syncthing_container,
    unifi_container,
    vaultwarden_container,
]
