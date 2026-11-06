"""
projects.homelab.monitoring.host_daemonset
==========================================

This module provisions DaemonSets for exporters that report on the Kubernetes host
itself, such as its hardware and kernel, rather than on a service. Each needs some
access to the host that a HomelabKubernetesDeployment does not grant, and must run
on every node, so these are DaemonSets of their own.
"""

from dataclasses import dataclass

from pulumi import Input, ResourceOptions
import pulumi_kubernetes as k8s


@dataclass
class HostDaemonSetResult:
    """
    The result of provisioning a host DaemonSet.
    """

    daemon_set: k8s.apps.v1.DaemonSet

    labels: dict[str, str]
    """
    The labels of the DaemonSet's pods, such as for a Service's selector.
    """

    label_selector: k8s.meta.v1.LabelSelectorArgs
    """
    Selects the DaemonSet's pods, such as for a Service or NetworkPolicy.
    """


def provision_host_daemon_set(
    resource_name: str,
    namespace: Input[str],
    name: str,
    containers: list[k8s.core.v1.ContainerArgs],
    opts: ResourceOptions,
    volumes: list[k8s.core.v1.VolumeArgs] | None = None,
    security_context: k8s.core.v1.PodSecurityContextArgs | None = None,
    host_network: bool = False,
    host_pid: bool = False,
) -> HostDaemonSetResult:
    """
    Provisions a DaemonSet that runs containers on every node. Its pods are labeled
    the way HomelabKubernetesDeployment labels its pods.
    """
    labels = {"service-name": name}
    label_selector = k8s.meta.v1.LabelSelectorArgs(match_labels=labels)

    daemon_set = k8s.apps.v1.DaemonSet(
        resource_name,
        metadata=k8s.meta.v1.ObjectMetaArgs(namespace=namespace, name=name),
        spec=k8s.apps.v1.DaemonSetSpecArgs(
            selector=label_selector,
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(labels=labels),
                spec=k8s.core.v1.PodSpecArgs(
                    containers=containers,
                    volumes=volumes,
                    security_context=security_context,
                    host_network=host_network or None,
                    host_pid=host_pid or None,
                    # A host exporter belongs on every node, including any that
                    # are tainted to keep ordinary workloads off.
                    tolerations=[
                        k8s.core.v1.TolerationArgs(
                            operator="Exists", effect="NoSchedule"
                        ),
                    ],
                ),
            ),
        ),
        opts=opts,
    )
    return HostDaemonSetResult(
        daemon_set=daemon_set, labels=labels, label_selector=label_selector
    )
