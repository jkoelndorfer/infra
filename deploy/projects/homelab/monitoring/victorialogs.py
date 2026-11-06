"""
projects.homelab.monitoring.victorialogs
========================================

This module provisions single-node VictoriaLogs [1], which stores logs and serves
LogsQL queries over them.

VictoriaLogs is not exposed through Traefik. It has no authentication of its own,
and only in-cluster clients need it: Fluent Bit sends it logs, Grafana queries it,
and VictoriaMetrics scrapes its metrics.

[1]: https://docs.victoriametrics.com/victorialogs/
"""

from dataclasses import dataclass
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
class VictoriaLogsArgs:
    """
    Arguments for provisioning VictoriaLogs.
    """

    namespace: Output[str]


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
            ],
            ports=[
                ContainerPortArgs(
                    container_port=HTTP_PORT,
                    name="http",
                    protocol="TCP",
                ),
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
