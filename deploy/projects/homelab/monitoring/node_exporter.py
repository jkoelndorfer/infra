"""
projects.homelab.monitoring.node_exporter
=========================================

This module provisions the node exporter [1], which reports the Kubernetes host's
own metrics: CPU, memory, disks and their I/O, filesystems, network interfaces, and
software RAID arrays.

The exporter reads the host's /proc and /sys, and its root filesystem, mounted read
only. It runs in the host's network namespace, so that it reports the host's
interfaces rather than its pod's, and in the host's PID namespace, so that it reads
the host's mounts and processes.

A pod in the host's network namespace is not selected by NetworkPolicies, and its
port is open on each of the host's addresses. The exporter therefore requires HTTP
basic authentication [2], with a password generated for VictoriaMetrics.

[1]: https://github.com/prometheus/node_exporter
[2]: https://github.com/prometheus/exporter-toolkit/blob/master/docs/web-configuration.md
"""

from dataclasses import dataclass
from ipaddress import IPv4Address
import json
from pathlib import PurePosixPath

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
import pulumi_random as random

from infralib import DeploymentContext

from ..kubernetes import uid_gid
from .host_daemonset import HostDaemonSetResult, provision_host_daemon_set
from .victoriametrics import ScrapeBasicAuth, ScrapeJob

SERVICE_NAME = "node-exporter"
IMAGE = "prom/node-exporter:v1.12.1"
HTTP_PORT = 9100

JOB_NAME = "node"

HOST_NAME = "kserv"
"""
The Kubernetes host's name, which its samples are given as the instance label. It
matches the host's infra DHCP assignment.
"""

SCRAPE_USER = "victoriametrics"

HOST_PROC = PurePosixPath("/host/proc")
HOST_SYS = PurePosixPath("/host/sys")
HOST_ROOT = PurePosixPath("/host/root")
WEB_CONFIG_DIRECTORY = PurePosixPath("/web")
WEB_CONFIG_FILE_NAME = "web.yml"

IGNORED_MOUNT_POINTS = (
    "^/(dev|proc|sys|run/credentials/.+|run/containerd/.+|run/k3s/.+"
    "|var/lib/kubelet/.+|var/lib/rancher/k3s/.+)($|/)"
)
"""
Mount points that the filesystem collector skips: the exporter's defaults [1], and
the mounts that k3s makes for each container and pod volume. A pod volume is a
directory of a filesystem that is reported already.

[1]: https://github.com/prometheus/node_exporter/blob/v1.12.1/collector/filesystem_linux.go
"""

IGNORED_NETWORK_DEVICES = "^(lo|veth.+)$"
"""
Network interfaces that are not reported. Each pod has a veth interface that lasts
only as long as the pod, and its traffic also crosses the pod bridge.
"""


@dataclass
class NodeExporterArgs:
    """
    Arguments for provisioning the node exporter.
    """

    namespace: Output[str]

    host_address: IPv4Address
    """
    The address of the Kubernetes host, which VictoriaMetrics scrapes the exporter
    at.
    """


@dataclass
class NodeExporterResult:
    """
    The result of provisioning the node exporter.
    """

    daemon_set: HostDaemonSetResult

    scrape_job: ScrapeJob
    """
    The job that scrapes the exporter.
    """


def provision_node_exporter(
    dctx: DeploymentContext,
    args: NodeExporterArgs,
    opts: ResourceOptions,
) -> NodeExporterResult:
    """
    Provisions the node exporter on every node, and returns the job that scrapes it.
    """
    password = random.RandomPassword(
        "node_exporter_scrape_password",
        length=32,
        lower=True,
        upper=True,
        numeric=True,
        special=False,
        opts=ResourceOptions(provider=dctx.provider_factory.random_provider()),
    )

    # The exporter reads its web configuration on each request, so a new password
    # takes effect without a restart.
    web_config = password.bcrypt_hash.apply(
        lambda bcrypt_hash: json.dumps(
            {"basic_auth_users": {SCRAPE_USER: bcrypt_hash}},
            indent=2,
            sort_keys=True,
        )
    )
    web_config_secret = k8s.core.v1.Secret(
        "node_exporter_web_config",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=f"{SERVICE_NAME}-web-config",
        ),
        string_data={WEB_CONFIG_FILE_NAME: web_config},
        opts=opts,
    )

    # NOTE: Mounts are not propagated from the host, because the host's root is a
    # private mount, which Kubernetes cannot propagate from. The pod sees the
    # filesystems that were mounted when it started. After mounting another
    # filesystem on the host, restart the exporter's pod to report it.
    host_mounts = {
        "proc": ("/proc", HOST_PROC),
        "sys": ("/sys", HOST_SYS),
        "root": ("/", HOST_ROOT),
    }

    service_user_group = uid_gid(dctx.target.environment, SERVICE_NAME)
    container = k8s.core.v1.ContainerArgs(
        name=SERVICE_NAME,
        image=IMAGE,
        image_pull_policy="IfNotPresent",
        command=[
            "/bin/node_exporter",
            f"--path.procfs={HOST_PROC}",
            f"--path.sysfs={HOST_SYS}",
            f"--path.rootfs={HOST_ROOT}",
            f"--path.udev.data={HOST_ROOT / 'run/udev/data'}",
            f"--web.listen-address=:{HTTP_PORT}",
            f"--web.config.file={WEB_CONFIG_DIRECTORY / WEB_CONFIG_FILE_NAME}",
            f"--collector.filesystem.mount-points-exclude={IGNORED_MOUNT_POINTS}",
            f"--collector.netdev.device-exclude={IGNORED_NETWORK_DEVICES}",
            f"--collector.netclass.ignored-devices={IGNORED_NETWORK_DEVICES}",
        ],
        ports=[
            k8s.core.v1.ContainerPortArgs(
                container_port=HTTP_PORT,
                host_port=HTTP_PORT,
                name="http",
                protocol="TCP",
            ),
        ],
        security_context=k8s.core.v1.SecurityContextArgs(
            allow_privilege_escalation=False,
            read_only_root_filesystem=True,
            capabilities=k8s.core.v1.CapabilitiesArgs(drop=["ALL"]),
        ),
        volume_mounts=[
            *[
                k8s.core.v1.VolumeMountArgs(
                    name=name,
                    mount_path=str(mount_path),
                    read_only=True,
                )
                for name, (_, mount_path) in host_mounts.items()
            ],
            k8s.core.v1.VolumeMountArgs(
                name="web-config",
                mount_path=str(WEB_CONFIG_DIRECTORY),
                read_only=True,
            ),
        ],
    )

    daemon_set = provision_host_daemon_set(
        "node_exporter",
        args.namespace,
        SERVICE_NAME,
        [container],
        opts,
        volumes=[
            *[
                k8s.core.v1.VolumeArgs(
                    name=name,
                    host_path=k8s.core.v1.HostPathVolumeSourceArgs(
                        path=host_path, type="Directory"
                    ),
                )
                for name, (host_path, _) in host_mounts.items()
            ],
            k8s.core.v1.VolumeArgs(
                name="web-config",
                secret=k8s.core.v1.SecretVolumeSourceArgs(
                    secret_name=web_config_secret.metadata["name"],
                    default_mode=0o444,
                ),
            ),
        ],
        security_context=k8s.core.v1.PodSecurityContextArgs(
            run_as_user=service_user_group,
            run_as_group=service_user_group,
            run_as_non_root=True,
        ),
        host_network=True,
        host_pid=True,
    )

    scrape_job = ScrapeJob(
        name=JOB_NAME,
        targets=[f"{args.host_address}:{HTTP_PORT}"],
        relabel_configs=[
            # A name reads better than an address in dashboards.
            {"target_label": "instance", "replacement": HOST_NAME},
        ],
        auth=ScrapeBasicAuth(username=SCRAPE_USER, password=password.result),
    )
    return NodeExporterResult(daemon_set=daemon_set, scrape_job=scrape_job)
