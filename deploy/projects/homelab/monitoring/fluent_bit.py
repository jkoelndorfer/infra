"""
projects.homelab.monitoring.fluent_bit
======================================

This module provisions Fluent Bit [1], which collects the logs of every pod on each
node and sends them to VictoriaLogs.

Fluent Bit tails the container runtime's log files under /var/log/containers,
reassembles lines that the runtime split, and adds each pod's namespace, name,
container and labels, which it looks up through the Kubernetes API. Each pod's
containers are a VictoriaLogs stream of their own [2].

Fluent Bit keeps its read positions in a database, and buffers logs that
VictoriaLogs has not accepted yet, in a directory on the host, so that neither is
lost when its pod restarts. It reads every file that is on the node when it first
starts, which kubelet's log rotation limits to the most recent logs of each
container.

The log files belong to root and are not world readable, so Fluent Bit runs as
root. It drops every capability, so that the files' permissions still apply to it,
and mounts the host's logs read only.

A pod opts out of collection with the annotation `fluentbit.io/exclude: "true"`
[3].

[1]: https://docs.fluentbit.io/manual/installation/downloads/kubernetes
[2]: https://docs.victoriametrics.com/victorialogs/keyconcepts/#stream-fields
[3]: https://docs.fluentbit.io/manual/data-pipeline/filters/kubernetes#kubernetes-annotations
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlencode

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.rbac.v1 import (
    ClusterRole,
    ClusterRoleBinding,
    PolicyRuleArgs,
    RoleRefArgs,
    SubjectArgs,
)

from infralib import DeploymentContext

from .host_daemonset import HostDaemonSetResult, provision_host_daemon_set
from .node_exporter import HOST_NAME
from .victoriametrics import ScrapeJob
from .victorialogs import VictoriaLogsResult

SERVICE_NAME = "fluent-bit"
IMAGE = "fluent/fluent-bit:5.1.5"
HTTP_PORT = 2020

JOB_NAME = "fluent-bit"
METRICS_PATH = "/api/v2/metrics/prometheus"

HOST_LOGS = PurePosixPath("/var/log")
"""
The host's log directory. It is mounted at the same path, because the files in
/var/log/containers are symbolic links into /var/log/pods.
"""

CONFIG_DIRECTORY = PurePosixPath("/config")
CONFIG_FILE_NAME = "fluent-bit.yaml"
STATE_DIRECTORY = PurePosixPath("/state")

BUFFER_LIMIT = "1G"
"""
The most that Fluent Bit buffers on the host while VictoriaLogs is unavailable. It
drops the oldest buffered logs beyond this.
"""

NAMESPACE_FIELD = "kubernetes.namespace_name"
POD_FIELD = "kubernetes.pod_name"
CONTAINER_FIELD = "kubernetes.container_name"

STREAM_FIELDS = [NAMESPACE_FIELD, POD_FIELD, CONTAINER_FIELD]
"""
The fields that identify a log stream in VictoriaLogs, which flattens Fluent Bit's
nested kubernetes record into dotted field names.
"""


@dataclass
class FluentBitArgs:
    """
    Arguments for provisioning Fluent Bit.
    """

    namespace: Output[str]
    victorialogs: VictoriaLogsResult


@dataclass
class FluentBitResult:
    """
    The result of provisioning Fluent Bit.
    """

    daemon_set: HostDaemonSetResult

    scrape_job: ScrapeJob
    """
    The job that scrapes Fluent Bit's own metrics.
    """


def provision_fluent_bit(
    dctx: DeploymentContext,
    args: FluentBitArgs,
    opts: ResourceOptions,
) -> FluentBitResult:
    """
    Provisions Fluent Bit on every node, and the service that VictoriaMetrics scrapes
    it through.
    """
    config = args.victorialogs.host.apply(
        lambda host: json.dumps(
            _config(host, args.victorialogs.port), indent=2, sort_keys=True
        )
    )

    # Fluent Bit reads its configuration at startup. Autonaming is verbatim, so a
    # content hash in the name is what rolls the pods on a change.
    config_map = k8s.core.v1.ConfigMap(
        "fluent_bit_config",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=config.apply(
                lambda c: f"{SERVICE_NAME}-{hashlib.sha256(c.encode()).hexdigest()[:8]}"
            ),
        ),
        data={CONFIG_FILE_NAME: config},
        opts=opts,
    )

    service_account = _provision_service_account(dctx, args, opts)

    container = k8s.core.v1.ContainerArgs(
        name=SERVICE_NAME,
        image=IMAGE,
        image_pull_policy="IfNotPresent",
        command=[
            "/fluent-bit/bin/fluent-bit",
            f"--config={CONFIG_DIRECTORY / CONFIG_FILE_NAME}",
        ],
        ports=[
            k8s.core.v1.ContainerPortArgs(
                container_port=HTTP_PORT,
                name="http",
                protocol="TCP",
            ),
        ],
        security_context=k8s.core.v1.SecurityContextArgs(
            run_as_user=0,
            run_as_group=0,
            allow_privilege_escalation=False,
            read_only_root_filesystem=True,
            capabilities=k8s.core.v1.CapabilitiesArgs(drop=["ALL"]),
        ),
        volume_mounts=[
            k8s.core.v1.VolumeMountArgs(
                name="logs", mount_path=str(HOST_LOGS), read_only=True
            ),
            k8s.core.v1.VolumeMountArgs(
                name="state", mount_path=str(STATE_DIRECTORY), read_only=False
            ),
            k8s.core.v1.VolumeMountArgs(
                name="config", mount_path=str(CONFIG_DIRECTORY), read_only=True
            ),
        ],
    )

    daemon_set = provision_host_daemon_set(
        "fluent_bit",
        args.namespace,
        SERVICE_NAME,
        [container],
        opts,
        volumes=[
            k8s.core.v1.VolumeArgs(
                name="logs",
                host_path=k8s.core.v1.HostPathVolumeSourceArgs(
                    path=str(HOST_LOGS), type="Directory"
                ),
            ),
            k8s.core.v1.VolumeArgs(
                name="state",
                host_path=k8s.core.v1.HostPathVolumeSourceArgs(
                    # Each environment collects every pod's logs, so each keeps
                    # read positions of its own.
                    path=f"/var/lib/{dctx.target.environment}-{SERVICE_NAME}",
                    type="DirectoryOrCreate",
                ),
            ),
            k8s.core.v1.VolumeArgs(
                name="config",
                config_map=k8s.core.v1.ConfigMapVolumeSourceArgs(
                    name=config_map.metadata["name"],
                    default_mode=0o444,
                ),
            ),
        ],
        service_account_name=service_account.metadata["name"],
    )

    k8s.core.v1.Service(
        "fluent_bit_service",
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

    # The service balances across every node's Fluent Bit, which reports the right
    # host only while there is one node.
    scrape_job = ScrapeJob(
        name=JOB_NAME,
        targets=[f"{SERVICE_NAME}:{HTTP_PORT}"],
        metrics_path=METRICS_PATH,
        relabel_configs=[
            {"target_label": "instance", "replacement": HOST_NAME},
        ],
    )
    return FluentBitResult(daemon_set=daemon_set, scrape_job=scrape_job)


def _provision_service_account(
    dctx: DeploymentContext,
    args: FluentBitArgs,
    opts: ResourceOptions,
) -> k8s.core.v1.ServiceAccount:
    """
    Provisions the service account that Fluent Bit looks up pod metadata as, with
    read access to every namespace's pods.
    """
    service_account = k8s.core.v1.ServiceAccount(
        "fluent_bit",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
        ),
        opts=opts,
    )

    # Cluster roles are not namespaced, so each environment's has a name of its own.
    cluster_role_name = f"{dctx.target.environment}-{SERVICE_NAME}"
    cluster_role = ClusterRole(
        "fluent_bit",
        metadata=k8s.meta.v1.ObjectMetaArgs(name=cluster_role_name),
        rules=[
            PolicyRuleArgs(
                api_groups=[""],
                resources=["namespaces", "pods"],
                verbs=["get", "list", "watch"],
            ),
        ],
        opts=opts,
    )
    ClusterRoleBinding(
        "fluent_bit",
        metadata=k8s.meta.v1.ObjectMetaArgs(name=cluster_role_name),
        role_ref=RoleRefArgs(
            api_group="rbac.authorization.k8s.io",
            kind="ClusterRole",
            name=cluster_role.metadata["name"],
        ),
        subjects=[
            SubjectArgs(
                kind="ServiceAccount",
                namespace=args.namespace,
                name=service_account.metadata["name"],
            ),
        ],
        opts=opts,
    )
    return service_account


def _config(victorialogs_host: str, victorialogs_port: int) -> dict[str, Any]:
    """
    Returns Fluent Bit's YAML configuration [1]. YAML is a superset of JSON, so
    Fluent Bit can read this as YAML.

    [1]: https://docs.fluentbit.io/manual/administration/configuring-fluent-bit/yaml
    """
    tag_prefix = "kube."
    # VictoriaLogs takes the fields' roles as query parameters [1].
    #
    # [1]: https://docs.victoriametrics.com/victorialogs/data-ingestion/fluentbit/
    insert_query = urlencode(
        {
            "_stream_fields": ",".join(STREAM_FIELDS),
            "_msg_field": "log",
            "_time_field": "date",
            # The container runtime's flag for a partial line, which the CRI
            # parser has already acted on.
            "ignore_fields": "_p",
        },
        safe=",",
    )
    return {
        "service": {
            "flush": "1",
            "log_level": "info",
            "http_server": "on",
            "http_listen": "0.0.0.0",
            "http_port": str(HTTP_PORT),
            "storage.path": str(STATE_DIRECTORY / "buffer"),
            "storage.sync": "normal",
            "storage.backlog.mem_limit": "5M",
        },
        "pipeline": {
            "inputs": [
                {
                    "name": "tail",
                    "tag": f"{tag_prefix}*",
                    "path": str(HOST_LOGS / "containers" / "*.log"),
                    "multiline.parser": "cri",
                    "db": str(STATE_DIRECTORY / "tail.db"),
                    "db.locking": "true",
                    "read_from_head": "true",
                    # Picks up new pods' logs sooner than the default minute.
                    "refresh_interval": "10",
                    "skip_long_lines": "on",
                    "storage.type": "filesystem",
                },
            ],
            "filters": [
                {
                    "name": "kubernetes",
                    "match": f"{tag_prefix}*",
                    # Tail tags each record with its file's path, dotted, after
                    # the input's tag prefix.
                    "kube_tag_prefix": f"{tag_prefix}var.log.containers.",
                    "labels": "on",
                    "annotations": "off",
                    # The API's answer for a pod with many labels can exceed the
                    # default buffer, which leaves its logs without metadata.
                    "buffer_size": "0",
                    "k8s-logging.exclude": "on",
                    "k8s-logging.parser": "off",
                },
            ],
            "outputs": [
                {
                    "name": "http",
                    "match": f"{tag_prefix}*",
                    "host": victorialogs_host,
                    "port": str(victorialogs_port),
                    "uri": f"/insert/jsonline?{insert_query}",
                    "format": "json_lines",
                    "json_date_key": "date",
                    "json_date_format": "iso8601",
                    "compress": "gzip",
                    # Retries until VictoriaLogs accepts the logs, which the
                    # buffer's limit bounds.
                    "retry_limit": "no_limits",
                    "storage.total_limit_size": BUFFER_LIMIT,
                },
            ],
        },
    }
