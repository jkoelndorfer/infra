"""
projects.homelab.blocky.project
===============================

This module contains the InfrastructureProject for Blocky, a DNS ad blocker.

Blocky logs every query as JSON, so that VictoriaLogs can break lookups down by
domain and client. It names clients after the homelab's DHCP assignments, and logs
other clients by address. Its HTTP port serves Prometheus metrics, and an API that
is not authenticated, so only homelab.monitoring's VictoriaMetrics may reach it.

The Blocky configuration is documented at [1].

[1]: https://0xerr0r.github.io/blocky/latest/configuration/
"""

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any

from pulumi import export, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import (
    ConfigMapVolumeSourceArgs,
    ContainerPortArgs,
    EnvVarArgs,
)

from infralib import (
    DeploymentContext,
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import (
    HomelabContainerConfigMapVolumeArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    namespace,
)


@dataclass
class BlockyMetricsEndpoint:
    """
    Where Blocky serves its Prometheus metrics.
    """

    namespace: str
    """
    The Kubernetes namespace that Blocky runs in.
    """

    target: str
    """
    The in-cluster host:port that the metrics are scraped from.
    """

    path: str
    """
    The HTTP path that the metrics are scraped at.
    """


class HomelabBlockyProject(InfrastructureProject):
    """
    Project that provisions Blocky on the homelab Kubernetes cluster.
    """

    name = "homelab.blocky"
    service_name = "blocky"

    image = "spx01/blocky:v0.32.1"

    config_directory = PurePosixPath("/config")
    config_file_name = "main.yml"

    container_dns_port = 5353
    container_http_port = 4000
    metrics_path = "/metrics"

    # The labels of the pods that scrape the metrics, and of their namespaces. These
    # are homelab.monitoring's VictoriaMetrics pods, in each of its environments.
    # They are spelled out because homelab.monitoring depends on this project.
    metrics_scraper_namespace_labels = {"local/name": "monitoring"}
    metrics_scraper_pod_labels = {"service-name": "victoriametrics"}

    ad_denylists = ["https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"]

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        # Blocky binds a host port, so a second environment would collide with
        # this one if scheduled on the same node.
        return [DeploymentTarget(Environment.PROD, None)]

    @classmethod
    def metrics_endpoint(cls, dctx: DeploymentContext) -> BlockyMetricsEndpoint:
        """
        Returns where Blocky serves its Prometheus metrics.
        """
        # NOTE: These outputs exist only once this stack has been up'd with metrics
        # support.
        outputs = dctx.outputs(cls.stack(DeploymentTarget(Environment.PROD, None)))
        svc = outputs["metrics_service"].value
        return BlockyMetricsEndpoint(
            namespace=svc["namespace"],
            target=f"{svc['name']}.{svc['namespace']}.svc:{svc['port']}",
            path=cls.metrics_path,
        )

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)

        # NOTE: The legacy homelab_blocky Terragrunt unit owns resources with the
        # same names, and its selector labels differ. Destroy that unit before
        # the first up of this stack. LAN clients using Blocky lose DNS until
        # this stack is up.
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        # YAML is a superset of JSON, so Blocky can read this as its YAML config.
        config = json.dumps(self._config(), indent=2, sort_keys=True)

        # Blocky reads its configuration only at startup. Autonaming is verbatim,
        # so a content hash in the name is what rolls the pod on a config change.
        config_hash = hashlib.sha256(config.encode()).hexdigest()[:8]
        config_map = k8s.core.v1.ConfigMap(
            "config",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name=f"{self.service_name}-{config_hash}",
            ),
            data={self.config_file_name: config},
            opts=self.default_ropts,
        )

        self.deployment = HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                env=[
                    EnvVarArgs(
                        name="BLOCKY_CONFIG_FILE",
                        value=str(self.config_directory / self.config_file_name),
                    ),
                ],
                image=self.image,
                ports=[
                    ContainerPortArgs(
                        container_port=self.container_dns_port,
                        host_port=self.dctx.config.homelab.network.ports.dns,
                        protocol="UDP",
                    ),
                    ContainerPortArgs(
                        container_port=self.container_http_port,
                        name="http",
                        protocol="TCP",
                    ),
                ],
                privilege_drop_mode="pod-exec",
                volumes=[],
                config_map_volumes=[
                    HomelabContainerConfigMapVolumeArgs(
                        name="config",
                        mount_path=str(self.config_directory),
                        config_map=ConfigMapVolumeSourceArgs(
                            name=config_map.metadata["name"],
                            default_mode=0o444,
                        ),
                    ),
                ],
            ),
            dctx=self.dctx,
            opts=self.default_ropts,
        )

        k8s.core.v1.Service(
            "metrics_service",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name=self.deployment.http_service_name,
            ),
            spec=k8s.core.v1.ServiceSpecArgs(
                type=k8s.core.v1.ServiceSpecType.CLUSTER_IP,
                selector=self.deployment.service_label,
                ports=[
                    k8s.core.v1.ServicePortArgs(
                        port=self.container_http_port,
                        target_port="http",
                        name="http",
                    ),
                ],
            ),
            opts=self.default_ropts,
        )

        self._provision_ingress_policies()

        export(
            "metrics_service",
            {
                "name": self.deployment.http_service_name,
                "namespace": self.ns_name,
                "port": self.container_http_port,
            },
        )

    def _provision_ingress_policies(self) -> None:
        """
        Provisions the policies that admit DNS queries from anywhere, and only the
        scrapers to the HTTP port. Selecting the pod isolates it, so these are all
        the ingress it accepts.
        """
        # Queries arrive through the host port, which forwards them to the pod's
        # port with their source address intact.
        k8s.networking.v1.NetworkPolicy(
            "dns",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="dns",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=self.deployment.label_selector,
                policy_types=["Ingress"],
                ingress=[
                    k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                        from_=[
                            k8s.networking.v1.NetworkPolicyPeerArgs(
                                ip_block=k8s.networking.v1.IPBlockArgs(
                                    cidr="0.0.0.0/0"
                                ),
                            )
                        ],
                        ports=[
                            k8s.networking.v1.NetworkPolicyPortArgs(
                                port=self.container_dns_port,
                                protocol="UDP",
                            ),
                        ],
                    ),
                ],
            ),
            opts=self.default_ropts,
        )

        # The HTTP port also serves an API that can disable blocking, which is not
        # authenticated, so nothing but the scrapers may reach it.
        k8s.networking.v1.NetworkPolicy(
            "metrics",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="metrics",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=self.deployment.label_selector,
                policy_types=["Ingress"],
                ingress=[
                    k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                        from_=[
                            k8s.networking.v1.NetworkPolicyPeerArgs(
                                namespace_selector=k8s.meta.v1.LabelSelectorArgs(
                                    match_labels=self.metrics_scraper_namespace_labels,
                                ),
                                pod_selector=k8s.meta.v1.LabelSelectorArgs(
                                    match_labels=self.metrics_scraper_pod_labels,
                                ),
                            )
                        ],
                        ports=[
                            k8s.networking.v1.NetworkPolicyPortArgs(port="http"),
                        ],
                    ),
                ],
            ),
            opts=self.default_ropts,
        )

    def _config(self) -> dict[str, Any]:
        """
        Returns the Blocky configuration.
        """
        # Blocky runs on the infra network, where the router's DNS forwarder is the
        # DNS server that the router hands out. See the router's provisioning role.
        networks = self.dctx.config.homelab.network.networks
        upstream_dns_servers = [str(networks.infra.router_interface.ip)]

        return {
            "upstreams": {
                "groups": {
                    "default": upstream_dns_servers,
                },
            },
            "blocking": {
                "denylists": {
                    "ads": self.ad_denylists,
                },
                "clientGroupsBlock": {
                    "default": ["ads"],
                },
            },
            "clientLookup": {
                "clients": self._client_names(),
            },
            "ports": {
                "dns": self.container_dns_port,
                "http": self.container_http_port,
            },
            "prometheus": {
                "enable": True,
                "path": self.metrics_path,
            },
            # JSON lets VictoriaLogs read the fields of each query, such as its
            # domain and client.
            "log": {
                "format": "json",
            },
            "queryLog": {
                "type": "console",
            },
            "specialUseDomains": {
                "enable": False,
            },
        }

    def _client_names(self) -> dict[str, list[str]]:
        """
        Returns the addresses of each device that has a DHCP assignment, keyed by the
        device's name. Blocky logs queries and labels its metrics with these names.
        """
        # NOTE: The router does not publish its leases in DNS, so Blocky cannot look
        # names up in reverse. Clients with a dynamic lease are known by address.
        clients: dict[str, list[str]] = defaultdict(list)
        for network in self.dctx.config.homelab.network.networks.by_name.values():
            for assignment in [] if network.dhcp is None else network.dhcp.assignments:
                clients[assignment.name].append(str(assignment.ip))
        return {name: sorted(ips) for name, ips in sorted(clients.items())}
