"""
roles/miniserv/containers
-------------------------

This module defines the containers that run on miniserv.

Note: containers defined here have volumes whose sources
are not absolute paths. These are transformed into absolute
paths during provisioning.
"""

from os import path

from lib.aws import ssm_parameter_value
from lib.model.container import Volume as V, VolumeSubdir as SD
from lib.pyinfra import Pyinfra
from lib.vars import (
    dns_zone,
    home_router_ip,
    miniserv_domains,
    miniserv_domains_by_service,
    timezone,
)
from .containerlib import MiniservContainer, swag_networks, web_networks
from .vars import files_dir


def pihole_env():
    return {
        "TZ": timezone,
        "DNS1": home_router_ip,
        "DNS2": "no",
        "VIRTUAL_HOST": miniserv_domains_by_service["pihole"],
    }


pihole_container = MiniservContainer.restarting(
    name="pihole",
    image="docker.io/pihole/pihole:v5.8.1",
    get_environment=pihole_env,
    deploy_config=None,
    volumes=[
        V(
            name="pi-hole",
            src="pi-hole",
            dest="/etc/pihole",
            mode="0755",
        ),
        V(
            name="dnsmasq",
            src="dnsmasq",
            dest="/etc/dnsmasq.d",
            mode="0755",
        ),
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


syncthing_container = MiniservContainer.restarting(
    name="syncthing",
    image="docker.io/linuxserver/syncthing:v1.21.0-ls83",
    get_environment=syncthing_env,
    deploy_config=None,
    volumes=[
        V(
            name="config",
            src="config",
            dest="/config",
            user="ctr",
            group="ctr",
        ),
        V(
            name="data",
            src="data",
            dest="/data",
            user="ctr",
            group="ctr",
        ),
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


unifi_container = MiniservContainer.restarting(
    name="unifi",
    image="docker.io/linuxserver/unifi-controller:7.3.76-ls174",
    get_environment=unifi_env,
    deploy_config=None,
    volumes=[
        V(
            name="config",
            src="config",
            dest="/config",
            user="ctr",
            group="ctr",
        ),
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
        "SMTP_PASSWORD": ssm_parameter_value("/prod/vaultwarden/sendgrid_api_key"),
        "SMTP_AUTH_MECHANISM": "Login",
    }


vaultwarden_container = MiniservContainer.restarting(
    name="vaultwarden",
    image="docker.io/vaultwarden/server:1.28.1",
    get_environment=vaultwarden_env,
    deploy_config=None,
    volumes=[
        V(
            name="data",
            src="data",
            dest="/data",
            user="ctr",
            group="ctr",
        ),
        V(
            name="log",
            src="log",
            dest="/log",
            user="ctr",
            group="ctr",
        ),
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
    subdomains = ",".join(s.replace(f".{dns_zone}", "") for s in miniserv_domains)
    return {
        "URL": dns_zone,
        "SUBDOMAINS": subdomains,
        "ONLY_SUBDOMAINS": "true",
        "EMAIL": f"letsencrypt@{dns_zone}",
        "VALIDATION": "http",  # TODO: Use DNS-based validation
        "STAGING": "false",
    }


def swag_config(pyinfra: Pyinfra, ctr: Container) -> bool:
    """
    Provisions configuration for the SWAG container.

    Returns `True` if any configuration has changed, `False` otherwise.
    """
    swag_files_dir = path.join(files_dir, "swag")
    config_dir = path.join(ctr.volume_named("config").src, "nginx", "proxy-confs")
    swag_configs = [
        "pihole",
        "syncthing",
        "unifi-controller",
        "vaultwarden",
    ]

    p = pyinfra.ctx("swag")
    ops = []
    for c in swag_configs:
        config_filename = f"{c}.subdomain.conf"
        op = p.files.put(
            name=f"deploy swag config: {c}",
            src=path.join(swag_files_dir, config_filename),
            dest=path.join(config_dir, config_filename),
            user="root",
            group="root",
            mode="0444",
        )
        ops.append(op)
    return any(o.changed for o in ops)


# NOTE: It's important that this container is defined _last_,
# so that swag_networks() can return all the requisite networks
# defined by previous containers.
swag_container = MiniservContainer.restarting(
    name="swag",
    image="docker.io/linuxserver/swag:1.31.0-ls155",
    get_environment=swag_environment,
    deploy_config=swag_config,
    volumes=[
        V(
            name="config",
            src="config",
            dest="/config",
            subdirs=[
                SD(
                    path="nginx",
                    user="ctr",
                    group="ctr",
                ),
                SD(
                    path="nginx/proxy-confs",
                    user="ctr",
                    group="ctr",
                ),
            ],
        ),
        V(
            name="vaultwarden-log",
            src=path.join(container_data_dir("vaultwarden"), "log"),
            dest="/vaultwarden-log",
            bind_mode="ro",
        ),
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
