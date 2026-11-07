"""
projects.homelab.vpn.project
============================

This module contains the InfrastructureProject for wg-easy, which provides a
WireGuard VPN endpoint and a web interface for managing its peers.

wg-easy's configuration is documented at [1] and [2], and its Prometheus metrics at
[3].

NOTE: wg-easy keeps its metrics settings in its database, so they cannot be set
here. To let homelab.monitoring scrape the metrics, enable Prometheus in the web
interface, under Admin Panel > General, and set its password to this stack's
metrics_password output.

[1]: https://wg-easy.github.io/wg-easy/latest/advanced/config/unattended-setup/
[2]: https://wg-easy.github.io/wg-easy/latest/advanced/config/optional-config/
[3]: https://wg-easy.github.io/wg-easy/latest/advanced/metrics/prometheus/
"""

from dataclasses import dataclass
from pathlib import PurePosixPath

from pulumi import export, Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import (
    CapabilitiesArgs,
    ContainerArgs,
    ContainerPortArgs,
    EnvVarArgs,
    EnvVarSourceArgs,
    SecretKeySelectorArgs,
    SecurityContextArgs,
)
import pulumi_random as random

from infralib import (
    DeploymentContext,
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ...dns.dyndns import DNSDynDNSProject
from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabHTTPSDeploymentIngressArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    namespace,
)
from ..traefik import HomelabTraefikProject


@dataclass
class VPNMetricsEndpoint:
    """
    Where wg-easy serves its Prometheus metrics, and how to authenticate to it.
    """

    namespace: str
    """
    The Kubernetes namespace that wg-easy runs in.
    """

    target: str
    """
    The in-cluster host:port that the metrics are scraped from.
    """

    path: str
    """
    The HTTP path that the metrics are scraped at.
    """

    token: Output[str]
    """
    The bearer token that the metrics endpoint requires.
    """


class HomelabVPNProject(InfrastructureProject):
    """
    Project that provisions wg-easy on the homelab Kubernetes cluster.

    Peers are given addresses on the wireguard_trusted network. wg-easy masquerades
    their traffic as the pod's address, so the rest of the homelab sees them as
    traffic from kserv rather than from the wireguard_trusted network.

    The masquerading is done with iptables on its nf_tables backend, in the pod's
    network namespace.
    """

    name = "homelab.vpn"
    service_name = "vpn"

    image = "ghcr.io/wg-easy/wg-easy:15.5.0"

    # NOTE: The image points iptables at its legacy backend, which needs the
    # ip_tables kernel modules. kserv does not load them, and the container cannot,
    # so wg-easy's hooks fail and it exits. This switches iptables to the nf_tables
    # backend, which the image also ships, and then runs the image's CMD. Keep it in
    # step with the image's CMD when upgrading.
    command = [
        "/bin/sh",
        "-c",
        "ln -sf iptables-nft /usr/sbin/iptables"
        " && ln -sf ip6tables-nft /usr/sbin/ip6tables"
        " && exec /usr/bin/dumb-init node server/index.mjs",
    ]

    backing_volume_id: HomelabBackingVolumeID = "data0"
    config_directory = PurePosixPath("/etc/wireguard")

    container_http_port = 51821
    metrics_path = "/metrics/prometheus"

    # The labels of the pods that scrape the metrics, and of their namespaces. These
    # are homelab.monitoring's VictoriaMetrics pods, in each of its environments.
    # They are spelled out because homelab.monitoring depends on this project.
    metrics_scraper_namespace_labels = {"local/name": "monitoring"}
    metrics_scraper_pod_labels = {"service-name": "victoriametrics"}

    admin_username = "admin"

    # NOTE: wg-easy requires an IPv6 CIDR alongside the IPv4 CIDR, even with IPv6
    # disabled. This is the unique local prefix from wg-easy's examples. It is never
    # used, because IPv6 is disabled.
    ipv6_cidr = "fdcc:ad94:bacf:61a3::/64"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [HomelabTraefikProject.stack(DeploymentTarget(Environment.PROD, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        # wg-easy binds a fixed host port, which the router forwards to, so a second
        # environment would collide with this one if scheduled on the same node.
        return [DeploymentTarget(Environment.PROD, None)]

    @classmethod
    def metrics_endpoint(cls, dctx: DeploymentContext) -> VPNMetricsEndpoint:
        """
        Returns where wg-easy serves its Prometheus metrics. See the module's NOTE
        on enabling them.
        """
        # NOTE: These outputs exist only once this stack has been up'd with metrics
        # support.
        outputs = dctx.outputs(cls.stack(DeploymentTarget(Environment.PROD, None)))
        svc = outputs["metrics_service"].value
        return VPNMetricsEndpoint(
            namespace=svc["namespace"],
            target=f"{svc['name']}.{svc['namespace']}.svc:{svc['port']}",
            path=cls.metrics_path,
            token=Output.secret(outputs["metrics_password"].value),
        )

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        network = self.dctx.config.homelab.network
        wireguard_port = network.ports.wireguard_trusted

        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        admin_password = random.RandomPassword(
            "admin_password",
            length=32,
            lower=True,
            upper=True,
            numeric=True,
            special=False,
            opts=ResourceOptions(provider=self.dctx.provider_factory.random_provider()),
        )
        admin_secret = k8s.core.v1.Secret(
            "admin",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="vpn-admin",
            ),
            string_data={"password": admin_password.result},
            opts=self.default_ropts,
        )

        # NOTE: The INIT_* variables only take effect on the first start, when wg-easy
        # creates its database. Afterwards, change these settings in the web
        # interface, or delete the config volume's contents to start over.
        init_env = {
            "INIT_ENABLED": "true",
            "INIT_USERNAME": self.admin_username,
            "INIT_HOST": DNSDynDNSProject.hostname(self.dctx.config),
            "INIT_PORT": str(wireguard_port),
            "INIT_DNS": str(network.networks.infra.router_interface),
            "INIT_IPV4_CIDR": str(network.networks.wireguard_trusted.ipv4_network),
            "INIT_IPV6_CIDR": self.ipv6_cidr,
        }
        env = [
            *[EnvVarArgs(name=k, value=v) for k, v in init_env.items()],
            EnvVarArgs(
                name="INIT_PASSWORD",
                value_from=EnvVarSourceArgs(
                    secret_key_ref=SecretKeySelectorArgs(
                        name=admin_secret.metadata["name"],
                        key="password",
                    ),
                ),
            ),
            # The homelab has no IPv6.
            EnvVarArgs(name="DISABLE_IPV6", value="true"),
            # Traefik reaches the web interface from a pod address, so trusting the
            # cluster network lets wg-easy log the client's address instead.
            EnvVarArgs(
                name="TRUSTED_PROXIES",
                value=str(network.networks.kube_cluster.ipv4_network),
            ),
        ]

        self.deployment = HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                https_ingress=HomelabHTTPSDeploymentIngressArgs(
                    container_port=self.container_http_port,
                ),
                image=self.image,
                command=self.command,
                env=env,
                ports=[
                    ContainerPortArgs(
                        container_port=wireguard_port,
                        host_port=wireguard_port,
                        protocol="UDP",
                    ),
                ],
                # wg-easy manages the WireGuard interface and its iptables rules
                # itself, so it runs as root with NET_ADMIN.
                privilege_drop_mode=None,
                security_context=SecurityContextArgs(
                    capabilities=CapabilitiesArgs(add=["NET_ADMIN"]),
                ),
                # NOTE: Kubernetes treats these sysctls as unsafe, so the pod
                # securityContext can only set them if the kubelet allows it. A
                # privileged init container sets them in the pod's network namespace
                # instead, without involving the kubelet.
                init_containers=[
                    ContainerArgs(
                        name="sysctl",
                        image=self.image,
                        command=[
                            "sysctl",
                            "-w",
                            "net.ipv4.ip_forward=1",
                            "net.ipv4.conf.all.src_valid_mark=1",
                        ],
                        security_context=SecurityContextArgs(privileged=True),
                    ),
                ],
                volumes=[
                    HomelabContainerVolumeArgs(
                        name="config",
                        mount_path=str(self.config_directory),
                        source=HomelabContainerVolumeProvisionedSource(
                            backing_volume=self.backing_volume_id,
                            storage="1Gi",
                            access_modes=["ReadWriteOnce"],
                            mode="0700",
                        ),
                        read_only=False,
                    ),
                ],
            ),
            dctx=self.dctx,
            opts=self.default_ropts,
        )

        # The deployment's Traefik-only policy isolates the pod, which would
        # otherwise drop WireGuard traffic arriving through the host port.
        k8s.networking.v1.NetworkPolicy(
            "wireguard",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="wireguard",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=self.deployment.label_selector,
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
                                port=wireguard_port,
                                protocol="UDP",
                            ),
                        ],
                    ),
                ],
            ),
            opts=self.default_ropts,
        )

        metrics_password = random.RandomPassword(
            "metrics_password",
            length=32,
            lower=True,
            upper=True,
            numeric=True,
            special=False,
            opts=ResourceOptions(provider=self.dctx.provider_factory.random_provider()),
        )

        # The deployment's Traefik-only policy would otherwise keep the scrapers from
        # reaching the web interface's port, which also serves the metrics.
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

        export("admin_username", self.admin_username)
        export("admin_password", admin_password.result)
        export("metrics_password", metrics_password.result)
        export(
            "metrics_service",
            {
                "name": self.deployment.http_service_name,
                "namespace": self.ns_name,
                "port": self.container_http_port,
            },
        )
