"""
roles/miniserv/containers
-------------------------

This module defines the containers that run on miniserv.

Note: containers defined here have volumes whose sources
are not absolute paths. These are transformed into absolute
paths during provisioning.
"""

from os import path
from typing import Mapping

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


def photoprism_env(ctr: MiniservContainer) -> Mapping[str, str]:
    return {
        "PHOTOPRISM_SITE_URL": "https://photoprism.johnk.io",

        # This account should *only* be used during initial setup.
        # If the credentials are required, log in to miniserv and
        # run `docker inspect` to get them.
        "PHOTOPRISM_ADMIN_USER": ssm_parameter_value("/prod/photoprism/username"),
        "PHOTOPRISM_ADMIN_PASSWORD": ssm_parameter_value("/prod/photoprism/password"),

        "PHOTOPRISM_DISABLE_CHOWN": "true",
        "PHOTOPRISM_INIT": "",

        # SWAG sits in front of Photoprism; all non-encrypted traffic is local
        "PHOTOPRISM_DISABLE_TLS": "true",
        "PHOTOPRISM_DEFAULT_TLS": "false",

        # It's a low-traffic installation of Photoprism. :-)
        "PHOTOPRISM_DATABASE_DRIVER": "sqlite",

        "PHOTOPRISM_DISABLE_TENSORFLOW": "true",

        "PHOTOPRISM_UID": str(ctr.uid),
        "PHOTOPRISM_GID": str(ctr.gid),
    }


photoprism_container = MiniservContainer.restarting(
    name="photoprism",
    image="docker.io/photoprism/photoprism:230719-ce",
    get_environment=photoprism_env,
    deploy_config=None,
    volumes=[
        V(
            name="import",
            src="import",
            dest="/photoprism/import",
            mode="0750",
            user="ctr",
            group="ctr",
        ),
        V(
            name="originals",
            src="originals",
            dest="/photoprism/originals",
            mode="0750",
            user="ctr",
            group="ctr",
        ),
        V(
            name="storage",
            src="storage",
            dest="/photoprism/storage",
            mode="0750",
            user="ctr",
            group="ctr",
        ),
    ],
    networks=web_networks("photoprism"),
    ports=[],

    # Photoprism only supports a limited range of UIDs & GIDs.
    # See their docker-compose file [1].
    #
    # [1]: https://dl.photoprism.app/docker/docker-compose.yml
    uid=1050,
    gid=1050,
)


def pihole_env(ctr: MiniservContainer):
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


def syncthing_env(ctr: MiniservContainer):
    return {
        "TZ": timezone,
    }


syncthing_container = MiniservContainer.restarting(
    name="syncthing",
    image="docker.io/linuxserver/syncthing:v1.27.10-ls154",
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


def unifi_env(ctr: MiniservContainer):
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


def vaultwarden_env(ctr: MiniservContainer):
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
    image="docker.io/vaultwarden/server:1.32.0",
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


def swag_environment(ctr: MiniservContainer):
    # SWAG expects a comma-separated list of only the host,
    # i.e. instead of "miniserv.johnk.io,pihole.johnk.io",
    # SWAG needs "miniserv,pihole".
    subdomains = ",".join(s.replace(f".{dns_zone}", "") for s in miniserv_domains)
    return {
        "URL": dns_zone,
        "SUBDOMAINS": subdomains,
        "ONLY_SUBDOMAINS": "true",
        "EMAIL": f"letsencrypt@{dns_zone}",
        "VALIDATION": "dns",
        "DNSPLUGIN": "route53",
        "STAGING": "false",
    }


def swag_config(pyinfra: Pyinfra, ctr: MiniservContainer) -> bool:
    """
    Provisions configuration for the SWAG container.

    Returns `True` if any configuration has changed, `False` otherwise.
    """
    swag_files_dir = path.join(files_dir, "swag")
    cfg_volume_src = ctr.volume_named("config").src
    proxy_confs_dir = path.join(cfg_volume_src, "nginx", "proxy-confs")
    dns_conf_dir = path.join(cfg_volume_src, "dns-conf")
    swag_configs = [
        "photoprism",
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
            dest=path.join(proxy_confs_dir, config_filename),
            user="root",
            group="root",
            mode="0444",
        )
        ops.append(op)

    op = p.files.template(
        name="deploy SWAG route53 dns config",
        src=path.join(swag_files_dir, "route53.ini.j2"),
        dest=path.join(dns_conf_dir, "route53.ini"),
        user="root",
        group="root",
        mode="0400",
        aws_access_key_id=ssm_parameter_value("/prod/local_ssl/aws_iam_access_key_id"),
        aws_secret_access_key=ssm_parameter_value("/prod/local_ssl/aws_iam_secret_access_key"),
    )
    ops.append(op)
    return any(o.changed for o in ops)


# NOTE: It's important that this container is defined _last_,
# so that swag_networks() can return all the requisite networks
# defined by previous containers.
swag_container = MiniservContainer.restarting(
    name="swag",
    image="docker.io/linuxserver/swag:2.11.0-ls319",
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
            src=path.join(vaultwarden_container.data_dir, "log"),
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
    photoprism_container,
    pihole_container,
    swag_container,
    syncthing_container,
    unifi_container,
    vaultwarden_container,
]
