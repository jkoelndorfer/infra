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
from pulumi_kubernetes.core.v1 import (
    ConfigMapVolumeSourceArgs,
    ContainerPortArgs,
    SecretVolumeSourceArgs,
)

from infralib import DeploymentContext

from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerConfigMapVolumeArgs,
    HomelabContainerSecretVolumeArgs,
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
SCRAPE_AUTH_DIRECTORY = PurePosixPath("/scrape-auth")

DEFAULT_METRICS_PATH = "/metrics"


@dataclass
class ScrapeBasicAuth:
    """
    HTTP basic authentication credentials that a scrape job sends to its targets.
    """

    username: str
    password: Output[str]


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
    The host:port of each endpoint. relabel_configs may turn these into something
    else, such as the devices that a multi-target exporter is asked about.
    """

    metrics_path: str = DEFAULT_METRICS_PATH
    """
    The HTTP path that each endpoint is scraped at.
    """

    params: dict[str, list[str]] = field(default_factory=dict)
    """
    URL query parameters sent with each scrape.
    """

    relabel_configs: list[dict[str, Any]] = field(default_factory=list)
    """
    Relabeling rules [1] that VictoriaMetrics applies to each target, before
    scraping it.

    [1]: https://docs.victoriametrics.com/victoriametrics/relabeling/
    """

    metric_relabel_configs: list[dict[str, Any]] = field(default_factory=list)
    """
    Relabeling rules [1] that VictoriaMetrics applies to each scraped sample,
    before storing it.

    [1]: https://docs.victoriametrics.com/victoriametrics/relabeling/
    """

    basic_auth: ScrapeBasicAuth | None = None
    """
    Credentials sent with each scrape, for targets that require authentication.
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


def multi_target_relabel_configs(exporter: str) -> list[dict[str, Any]]:
    """
    Returns relabeling rules for a multi-target exporter [1], which queries another
    device on each scrape. Each target is passed to the exporter at host:port as
    its target parameter, and is kept as the instance label.

    [1]: https://prometheus.io/docs/guides/multi-target-exporter/
    """
    return [
        {"source_labels": ["__address__"], "target_label": "__param_target"},
        {"source_labels": ["__param_target"], "target_label": "instance"},
        {"target_label": "__address__", "replacement": exporter},
    ]


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

    secret_volumes = _scrape_auth_secret_volumes(args, opts)

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
            secret_volumes=secret_volumes,
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


def _scrape_auth_secret_volumes(
    args: VictoriaMetricsArgs,
    opts: ResourceOptions,
) -> list[HomelabContainerSecretVolumeArgs]:
    """
    Provisions a secret that holds the password of each scrape job that has basic
    authentication, keyed by job name, and returns the volume that mounts it. Jobs
    read their password from the mounted file, so that it stays out of the scrape
    configuration's ConfigMap.
    """
    passwords = {
        job.name: job.basic_auth.password
        for job in args.scrape_jobs
        if job.basic_auth is not None
    }
    if not passwords:
        return []

    secret = k8s.core.v1.Secret(
        "victoriametrics_scrape_auth",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=f"{SERVICE_NAME}-scrape-auth",
        ),
        string_data=passwords,
        opts=opts,
    )
    return [
        HomelabContainerSecretVolumeArgs(
            name="scrape-auth",
            mount_path=str(SCRAPE_AUTH_DIRECTORY),
            secret=SecretVolumeSourceArgs(
                secret_name=secret.metadata["name"],
                default_mode=0o444,
            ),
        ),
    ]


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
    if job.metrics_path != DEFAULT_METRICS_PATH:
        config["metrics_path"] = job.metrics_path
    if job.params:
        config["params"] = job.params
    if job.relabel_configs:
        config["relabel_configs"] = job.relabel_configs
    if job.metric_relabel_configs:
        config["metric_relabel_configs"] = job.metric_relabel_configs
    if job.basic_auth is not None:
        config["basic_auth"] = {
            "username": job.basic_auth.username,
            "password_file": str(SCRAPE_AUTH_DIRECTORY / job.name),
        }
    return config
