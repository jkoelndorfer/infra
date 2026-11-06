"""
projects.homelab.monitoring.victorialogs
========================================

This module provisions single-node VictoriaLogs [1], which stores logs and serves
LogsQL queries over them.

VictoriaLogs is not exposed through Traefik. It has no authentication of its own,
and only in-cluster clients need its HTTP API: Fluent Bit sends it logs, Grafana
queries it, and VictoriaMetrics scrapes its metrics.

VictoriaLogs can also receive syslog [2] from the router and switches, on a port of
the Kubernetes host. It parses each message's host, application, severity and
facility into fields, and records the address that sent it as remote_ip. Each host's
application is a log stream of its own.

[1]: https://docs.victoriametrics.com/victorialogs/
[2]: https://docs.victoriametrics.com/victorialogs/data-ingestion/syslog/
"""

from dataclasses import dataclass
from ipaddress import IPv4Network
import json
from pathlib import PurePosixPath

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import ContainerPortArgs

from infralib import DeploymentContext

from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
)
from .victoriametrics import ScrapeJob

SERVICE_NAME = "victorialogs"
IMAGE = "victoriametrics/victoria-logs:v1.53.0"
HTTP_PORT = 9428

SYSLOG_PORT = 5140
"""
The port VictoriaLogs receives syslog on inside its pod. VictoriaLogs does not run
as root, so this is above the privileged ports; the host port maps the standard
port to it.
"""

SYSLOG_STREAM_FIELDS = ["hostname", "app_name"]
"""
The fields that identify a syslog stream. VictoriaLogs adds proc_id by default,
which would start a new stream each time a device's daemon restarts.
"""

JOB_NAME = "victorialogs"

BACKING_VOLUME: HomelabBackingVolumeID = "data0"
STORAGE_SIZE = "20Gi"
RETENTION_PERIOD = "30d"
"""
How long VictoriaLogs keeps logs. Logs serve troubleshooting, which seldom looks
back further than this.
"""

MAX_DISK_SPACE_USAGE = "15GiB"
"""
The space that VictoriaLogs may use before it drops its oldest days of logs, even
within the retention period. It is below STORAGE_SIZE, which the volume does not
enforce, so that a noisy pod cannot fill the backing volume that other services
share.
"""

STORAGE_PATH = PurePosixPath("/storage")


@dataclass
class VictoriaLogsSyslogArgs:
    """
    Arguments for receiving syslog over UDP on a port of the Kubernetes host.
    """

    host_port: int

    sources: list[IPv4Network]
    """
    The networks that may send syslog. There must be at least one, because a policy
    rule without sources would admit every address.
    """

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("syslog needs at least one source network")


@dataclass
class VictoriaLogsArgs:
    """
    Arguments for provisioning VictoriaLogs.
    """

    namespace: Output[str]

    syslog: VictoriaLogsSyslogArgs | None = None
    """
    How VictoriaLogs receives syslog. None to receive none.
    """


@dataclass
class VictoriaLogsResult:
    """
    The result of provisioning VictoriaLogs.
    """

    deployment: HomelabKubernetesDeployment

    host: Output[str]
    """
    The in-cluster host name of the VictoriaLogs service.
    """

    port: int
    """
    The port of the VictoriaLogs HTTP API.
    """

    url: Output[str]
    """
    The in-cluster URL of the VictoriaLogs HTTP API.
    """

    scrape_job: ScrapeJob
    """
    The job that scrapes VictoriaLogs' own metrics.
    """


def provision_victorialogs(
    dctx: DeploymentContext,
    args: VictoriaLogsArgs,
    opts: ResourceOptions,
) -> VictoriaLogsResult:
    """
    Provisions VictoriaLogs and the service that clients reach it through.
    """
    syslog_flags: list[str] = []
    syslog_ports: list[ContainerPortArgs] = []
    if args.syslog is not None:
        syslog_flags = [
            f"-syslog.listenAddr.udp=:{SYSLOG_PORT}",
            f"-syslog.streamFields.udp={json.dumps(SYSLOG_STREAM_FIELDS, separators=(',', ':'))}",
            "-syslog.useRemoteIP.udp=true",
        ]
        syslog_ports = [
            ContainerPortArgs(
                container_port=SYSLOG_PORT,
                host_port=args.syslog.host_port,
                name="syslog",
                protocol="UDP",
            ),
        ]

    deployment = HomelabKubernetesDeployment(
        name="victorialogs",
        args=HomelabKubernetesDeploymentArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
            image=IMAGE,
            command=[
                "/victoria-logs-prod",
                f"-httpListenAddr=:{HTTP_PORT}",
                f"-storageDataPath={STORAGE_PATH}",
                f"-retentionPeriod={RETENTION_PERIOD}",
                f"-retention.maxDiskSpaceUsageBytes={MAX_DISK_SPACE_USAGE}",
                *syslog_flags,
            ],
            ports=[
                ContainerPortArgs(
                    container_port=HTTP_PORT,
                    name="http",
                    protocol="TCP",
                ),
                *syslog_ports,
            ],
            privilege_drop_mode="pod-exec",
            volumes=[
                HomelabContainerVolumeArgs(
                    # Volumes are named after the namespace and this name, which
                    # VictoriaMetrics' volume already takes as storage.
                    name="logs",
                    mount_path=str(STORAGE_PATH),
                    source=HomelabContainerVolumeProvisionedSource(
                        backing_volume=BACKING_VOLUME,
                        storage=STORAGE_SIZE,
                        access_modes=["ReadWriteOnce"],
                        mode="0700",
                    ),
                    read_only=False,
                ),
            ],
        ),
        dctx=dctx,
        opts=opts,
    )

    service = k8s.core.v1.Service(
        "victorialogs_service",
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

    if args.syslog is not None:
        _provision_syslog_policy(args.namespace, deployment, args.syslog, opts)

    host = Output.concat(service.metadata["name"], ".", args.namespace, ".svc")
    url = Output.concat("http://", host, f":{HTTP_PORT}")
    scrape_job = ScrapeJob(
        name=JOB_NAME,
        targets=[f"{SERVICE_NAME}:{HTTP_PORT}"],
    )
    return VictoriaLogsResult(
        deployment=deployment,
        host=host,
        port=HTTP_PORT,
        url=url,
        scrape_job=scrape_job,
    )


def _provision_syslog_policy(
    namespace: Output[str],
    deployment: HomelabKubernetesDeployment,
    syslog: VictoriaLogsSyslogArgs,
    opts: ResourceOptions,
) -> None:
    """
    Provisions a policy that permits syslog from its sources. Another policy selects
    VictoriaLogs' pods to limit who reaches its HTTP API, which would otherwise drop
    syslog arriving through the host port.
    """
    k8s.networking.v1.NetworkPolicy(
        "victorialogs_syslog",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=namespace,
            name=f"{SERVICE_NAME}-syslog",
        ),
        spec=k8s.networking.v1.NetworkPolicySpecArgs(
            pod_selector=deployment.label_selector,
            policy_types=["Ingress"],
            ingress=[
                k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                    from_=[
                        k8s.networking.v1.NetworkPolicyPeerArgs(
                            ip_block=k8s.networking.v1.IPBlockArgs(cidr=str(source)),
                        )
                        for source in syslog.sources
                    ],
                    ports=[
                        k8s.networking.v1.NetworkPolicyPortArgs(
                            port="syslog", protocol="UDP"
                        ),
                    ],
                ),
            ],
        ),
        opts=opts,
    )
