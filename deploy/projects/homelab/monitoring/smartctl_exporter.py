"""
projects.homelab.monitoring.smartctl_exporter
=============================================

This module provisions the smartctl exporter [1], which reports the health of the
Kubernetes host's disks from their SMART data: overall status, temperature, power-on
time, and error counters such as reallocated sectors. It polls each disk with
smartctl on an interval of its own and serves the latest results, so scrapes do not
reach the disks.

Reading SMART data sends commands straight to the disks, which takes root and raw
access to the host's block devices. The exporter runs privileged, as its
documentation recommends [1]. It needs nothing else from the host, so it stays on
the pod network, where a NetworkPolicy can limit who reaches it.

NOTE: A privileged container sees the host's devices as they were when it started.
After adding a disk, restart the exporter's pod.

[1]: https://github.com/prometheus-community/smartctl_exporter
"""

from dataclasses import dataclass

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s

from .host_daemonset import HostDaemonSetResult, provision_host_daemon_set
from .node_exporter import HOST_NAME
from .victoriametrics import ScrapeJob

SERVICE_NAME = "smartctl-exporter"
IMAGE = "prometheuscommunity/smartctl-exporter:v0.15.0"
HTTP_PORT = 9633

JOB_NAME = "smartctl"


@dataclass
class SmartctlExporterArgs:
    """
    Arguments for provisioning the smartctl exporter.
    """

    namespace: Output[str]


@dataclass
class SmartctlExporterResult:
    """
    The result of provisioning the smartctl exporter.
    """

    daemon_set: HostDaemonSetResult

    scrape_job: ScrapeJob
    """
    The job that scrapes the exporter.
    """


def provision_smartctl_exporter(
    args: SmartctlExporterArgs,
    opts: ResourceOptions,
) -> SmartctlExporterResult:
    """
    Provisions the smartctl exporter on every node, and the service that
    VictoriaMetrics scrapes it through.

    The service balances across every node's exporter, which reports the right
    host only while there is one node.
    """
    container = k8s.core.v1.ContainerArgs(
        name=SERVICE_NAME,
        image=IMAGE,
        image_pull_policy="IfNotPresent",
        command=[
            "/bin/smartctl_exporter",
            f"--web.listen-address=:{HTTP_PORT}",
        ],
        ports=[
            k8s.core.v1.ContainerPortArgs(
                container_port=HTTP_PORT,
                name="http",
                protocol="TCP",
            ),
        ],
        security_context=k8s.core.v1.SecurityContextArgs(
            privileged=True,
            # The image runs as nobody, which cannot open the disks.
            run_as_user=0,
            run_as_group=0,
            read_only_root_filesystem=True,
        ),
    )

    daemon_set = provision_host_daemon_set(
        "smartctl_exporter",
        args.namespace,
        SERVICE_NAME,
        [container],
        opts,
    )

    k8s.core.v1.Service(
        "smartctl_exporter_service",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
        ),
        spec=k8s.core.v1.ServiceSpecArgs(
            type=k8s.core.v1.ServiceSpecType.CLUSTER_IP,
            selector=daemon_set.labels,
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

    scrape_job = ScrapeJob(
        name=JOB_NAME,
        targets=[f"{SERVICE_NAME}:{HTTP_PORT}"],
        relabel_configs=[
            {"target_label": "instance", "replacement": HOST_NAME},
        ],
    )
    return SmartctlExporterResult(daemon_set=daemon_set, scrape_job=scrape_job)
