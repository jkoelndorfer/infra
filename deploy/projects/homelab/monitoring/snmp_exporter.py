"""
projects.homelab.monitoring.snmp_exporter
=========================================

This module provisions the SNMP exporter [1], through which VictoriaMetrics
scrapes the router and switches. On each scrape, the exporter queries the device
named by the target parameter, walking the MIB modules named by the module
parameter.

The modules come from the configuration built into the exporter's image [2]. Only
the credentials are configured here.

The router and switches only answer SNMP from the Kubernetes host's address, which
the exporter's queries leave the cluster from.

[1]: https://github.com/prometheus/snmp_exporter
[2]: https://github.com/prometheus/snmp_exporter/blob/main/snmp.yml
"""

from dataclasses import dataclass
from ipaddress import IPv4Address
import json
from pathlib import PurePosixPath

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import ContainerPortArgs, SecretVolumeSourceArgs

from infralib import DeploymentContext
from infralib.config.homelab import HomelabNetworking

from ..kubernetes import (
    HomelabContainerSecretVolumeArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
)
from .victoriametrics import ScrapeJob, multi_target_relabel_configs

SERVICE_NAME = "snmp-exporter"
IMAGE = "prom/snmp-exporter:v0.30.1"
HTTP_PORT = 9116

BUILTIN_CONFIG_FILE = PurePosixPath("/etc/snmp_exporter/snmp.yml")
AUTH_DIRECTORY = PurePosixPath("/auth")
AUTH_FILE_NAME = "auth.yml"

AUTH = "homelab"
"""
The name of the exporter's credentials for homelab devices, which scrapes select
with the auth parameter.
"""

JOB_PREFIX = "snmp-"
"""
The prefix of each SNMP scrape job's name. The rest is the device's name.
"""

ROUTER_NAME = "router0"
"""
The router's name. It matches the host name in the router's configuration.
"""

ROUTER_MODULES = [
    "system",
    "if_mib",
    "hrStorage",
    "ucd_la_table",
    "ucd_memory",
    "ucd_system_stats",
]
"""
The modules walked on the router. EdgeOS runs net-snmp, so it serves the host
resources and UCD MIBs.
"""

SWITCH_MODULES = ["system", "if_mib"]
"""
The modules walked on switches.
"""


@dataclass
class SNMPDevice:
    """
    A device that the SNMP exporter is scraped for.
    """

    name: str
    """
    The device's name, which its samples are given as the instance label.
    """

    address: IPv4Address
    modules: list[str]


@dataclass
class SNMPExporterArgs:
    """
    Arguments for provisioning the SNMP exporter.
    """

    namespace: Output[str]
    community: str


@dataclass
class SNMPExporterResult:
    """
    The result of provisioning the SNMP exporter.
    """

    deployment: HomelabKubernetesDeployment


def snmp_devices(networking: HomelabNetworking) -> list[SNMPDevice]:
    """
    Returns the router, and each switch that has a management address.
    """
    devices = [
        SNMPDevice(
            name=ROUTER_NAME,
            # The router only listens for SNMP on its infra address.
            address=networking.networks.infra.router_interface.ip,
            modules=ROUTER_MODULES,
        ),
    ]
    devices += [
        SNMPDevice(name=s.name, address=s.address, modules=SWITCH_MODULES)
        for s in networking.switches
        if s.address is not None
    ]
    return devices


def snmp_scrape_job(device: SNMPDevice) -> ScrapeJob:
    """
    Returns the job that scrapes the exporter for one device.
    """
    return ScrapeJob(
        name=f"{JOB_PREFIX}{device.name}",
        targets=[str(device.address)],
        metrics_path="/snmp",
        params={"auth": [AUTH], "module": [",".join(device.modules)]},
        relabel_configs=[
            *multi_target_relabel_configs(f"{SERVICE_NAME}:{HTTP_PORT}"),
            # A name reads better than an address in dashboards.
            {"target_label": "instance", "replacement": device.name},
        ],
    )


def provision_snmp_exporter(
    dctx: DeploymentContext,
    args: SNMPExporterArgs,
    opts: ResourceOptions,
) -> SNMPExporterResult:
    """
    Provisions the SNMP exporter and the service that VictoriaMetrics scrapes it
    through.
    """
    # NOTE: The exporter only reads its configuration at startup. After the
    # community changes, restart its pod.
    #
    # The exporter can't read an SNMPv2c community from the environment, so it is
    # kept in a configuration file of its own. The exporter merges it with the
    # built-in configuration.
    auth_config = Output.secret(args.community).apply(
        lambda community: json.dumps(
            {"auths": {AUTH: {"version": 2, "community": community}}},
            indent=2,
            sort_keys=True,
        )
    )
    auth_secret = k8s.core.v1.Secret(
        "snmp_exporter_auth",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=f"{SERVICE_NAME}-auth",
        ),
        string_data={AUTH_FILE_NAME: auth_config},
        opts=opts,
    )

    deployment = HomelabKubernetesDeployment(
        name="snmp_exporter",
        args=HomelabKubernetesDeploymentArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
            image=IMAGE,
            command=[
                "/bin/snmp_exporter",
                f"--config.file={BUILTIN_CONFIG_FILE}",
                f"--config.file={AUTH_DIRECTORY / AUTH_FILE_NAME}",
                f"--web.listen-address=:{HTTP_PORT}",
            ],
            ports=[
                ContainerPortArgs(
                    container_port=HTTP_PORT,
                    name="http",
                    protocol="TCP",
                ),
            ],
            privilege_drop_mode="pod-exec",
            volumes=[],
            secret_volumes=[
                HomelabContainerSecretVolumeArgs(
                    name="auth",
                    mount_path=str(AUTH_DIRECTORY),
                    secret=SecretVolumeSourceArgs(
                        secret_name=auth_secret.metadata["name"],
                        default_mode=0o444,
                    ),
                ),
            ],
        ),
        dctx=dctx,
        opts=opts,
    )

    k8s.core.v1.Service(
        "snmp_exporter_service",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
        ),
        spec=k8s.core.v1.ServiceSpecArgs(
            type=k8s.core.v1.ServiceSpecType.CLUSTER_IP,
            selector=deployment.service_label,
            ports=[
                k8s.core.v1.ServicePortArgs(
                    port=HTTP_PORT,
                    target_port="http",
                    name="http",
                ),
            ],
        ),
        opts=opts,
    )

    return SNMPExporterResult(deployment=deployment)
