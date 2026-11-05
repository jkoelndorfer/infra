"""
projects.homelab.monitoring.victoriametrics
===========================================

This module provisions single-node VictoriaMetrics [1], which scrapes metrics
targets and stores the results.

VictoriaMetrics is not exposed through Traefik. It has no authentication of its
own, and only in-cluster clients need it.

[1]: https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/
"""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import ConfigMapVolumeSourceArgs, ContainerPortArgs

from infralib import DeploymentContext

from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerConfigMapVolumeArgs,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
)

SERVICE_NAME = "victoriametrics"
IMAGE = "victoriametrics/victoria-metrics:v1.154.1"
HTTP_PORT = 8428

BACKING_VOLUME: HomelabBackingVolumeID = "data0"
STORAGE_SIZE = "20Gi"
RETENTION_PERIOD = "2y"
"""
How long VictoriaMetrics keeps samples. Sensor history is the main reason to
keep data this long.
"""

SCRAPE_INTERVAL = "30s"

STORAGE_PATH = PurePosixPath("/storage")
CONFIG_DIRECTORY = PurePosixPath("/config")
SCRAPE_CONFIG_FILE_NAME = "scrape.yml"


@dataclass
class ScrapeJob:
    """
    A set of Prometheus-format endpoints that VictoriaMetrics scrapes.
    """

    name: str
    """
    The job name, which VictoriaMetrics attaches to each sample as the job label.
    """

    targets: list[str]
    """
    The host:port of each endpoint, scraped at /metrics.
    """

    metric_relabel_configs: list[dict[str, Any]] = field(default_factory=list)
    """
    Relabeling rules [1] that VictoriaMetrics applies to each scraped sample,
    before storing it.

    [1]: https://docs.victoriametrics.com/victoriametrics/relabeling/
    """


@dataclass
class VictoriaMetricsArgs:
    """
    Arguments for provisioning VictoriaMetrics.
    """

    namespace: Output[str]
    scrape_jobs: list[ScrapeJob]


@dataclass
class VictoriaMetricsResult:
    """
    The result of provisioning VictoriaMetrics.
    """

    deployment: HomelabKubernetesDeployment

    url: Output[str]
    """
    The in-cluster URL of the VictoriaMetrics HTTP API.
    """


def provision_victoriametrics(
    dctx: DeploymentContext,
    args: VictoriaMetricsArgs,
    opts: ResourceOptions,
) -> VictoriaMetricsResult:
    """
    Provisions VictoriaMetrics and the service that clients reach it through.
    """
    # YAML is a superset of JSON, so VictoriaMetrics can read this as YAML.
    scrape_config = json.dumps(_scrape_config(args), indent=2, sort_keys=True)

    # VictoriaMetrics reads its scrape configuration at startup. Autonaming is
    # verbatim, so a content hash in the name is what rolls the pod on a change.
    config_hash = hashlib.sha256(scrape_config.encode()).hexdigest()[:8]
    config_map = k8s.core.v1.ConfigMap(
        "victoriametrics_config",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=f"{SERVICE_NAME}-{config_hash}",
        ),
        data={SCRAPE_CONFIG_FILE_NAME: scrape_config},
        opts=opts,
    )

    deployment = HomelabKubernetesDeployment(
        name="victoriametrics",
        args=HomelabKubernetesDeploymentArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
            image=IMAGE,
            command=[
                "/victoria-metrics-prod",
                f"-httpListenAddr=:{HTTP_PORT}",
                f"-storageDataPath={STORAGE_PATH}",
                f"-retentionPeriod={RETENTION_PERIOD}",
                f"-promscrape.config={CONFIG_DIRECTORY / SCRAPE_CONFIG_FILE_NAME}",
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
                    name="storage",
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
            config_map_volumes=[
                HomelabContainerConfigMapVolumeArgs(
                    name="config",
                    mount_path=str(CONFIG_DIRECTORY),
                    config_map=ConfigMapVolumeSourceArgs(
                        name=config_map.metadata["name"],
                        default_mode=0o444,
                    ),
                ),
            ],
        ),
        dctx=dctx,
        opts=opts,
    )

    service = k8s.core.v1.Service(
        "victoriametrics_service",
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

    url = Output.concat(
        "http://",
        service.metadata["name"],
        ".",
        args.namespace,
        f".svc:{HTTP_PORT}",
    )
    return VictoriaMetricsResult(deployment=deployment, url=url)


def _scrape_config(args: VictoriaMetricsArgs) -> dict[str, Any]:
    """
    Returns the Prometheus-compatible scrape configuration [1].

    [1]: https://docs.victoriametrics.com/victoriametrics/sd_configs/
    """
    return {
        "global": {
            "scrape_interval": SCRAPE_INTERVAL,
        },
        "scrape_configs": [_scrape_job_config(job) for job in args.scrape_jobs],
    }


def _scrape_job_config(job: ScrapeJob) -> dict[str, Any]:
    """
    Returns the configuration of one scrape job.
    """
    config: dict[str, Any] = {
        "job_name": job.name,
        "static_configs": [{"targets": job.targets}],
    }
    if job.metric_relabel_configs:
        config["metric_relabel_configs"] = job.metric_relabel_configs
    return config
