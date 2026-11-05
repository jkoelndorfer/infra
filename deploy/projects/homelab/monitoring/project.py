"""
projects.homelab.monitoring.project
===================================

This module contains the InfrastructureProject for homelab monitoring: VictoriaMetrics
stores metrics, and Grafana visualizes them. The SNMP exporter collects metrics from
the router and switches.
"""

from pulumi import ResourceOptions
import pulumi_kubernetes as k8s

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import HomelabKubernetesDeployment, namespace
from ..traefik import HomelabTraefikProject
from .grafana import GrafanaArgs, provision_grafana
from .snmp_exporter import (
    SNMPExporterArgs,
    provision_snmp_exporter,
    snmp_devices,
    snmp_scrape_job,
)
from .traefik_metrics import traefik_metric_relabel_configs
from .victoriametrics import (
    ScrapeJob,
    VictoriaMetricsArgs,
    provision_victoriametrics,
)


class HomelabMonitoringProject(InfrastructureProject):
    name = "homelab.monitoring"
    service_name = "monitoring"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [HomelabTraefikProject.stack(DeploymentTarget(Environment.PROD, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(e, None) for e in [Environment.DEV, Environment.PROD]]

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        networking = self.dctx.config.homelab.network
        snmp_exporter = provision_snmp_exporter(
            self.dctx,
            SNMPExporterArgs(
                namespace=self.ns_name,
                community=networking.snmp.community,
            ),
            self.default_ropts,
        )

        vm = provision_victoriametrics(
            self.dctx,
            VictoriaMetricsArgs(
                namespace=self.ns_name,
                scrape_jobs=[
                    ScrapeJob(
                        name="traefik",
                        targets=[HomelabTraefikProject.metrics_target(self.dctx)],
                        metric_relabel_configs=traefik_metric_relabel_configs(),
                    ),
                    *[snmp_scrape_job(d) for d in snmp_devices(networking)],
                ],
            ),
            self.default_ropts,
        )

        grafana = provision_grafana(
            self.dctx,
            GrafanaArgs(
                namespace=self.ns_name,
                victoriametrics=vm,
            ),
            self.default_ropts,
        )

        self._provision_ingress_policy(
            "victoriametrics", vm.deployment, grafana.deployment
        )
        self._provision_ingress_policy(
            "snmp_exporter", snmp_exporter.deployment, vm.deployment
        )

    def _provision_ingress_policy(
        self,
        name: str,
        server: HomelabKubernetesDeployment,
        client: HomelabKubernetesDeployment,
    ) -> None:
        """
        Provisions a policy that permits only the client's pods to reach the server's
        HTTP port. Selecting the server's pods denies all other ingress to them.
        """
        k8s.networking.v1.NetworkPolicy(
            f"{name}_ingress",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name=f"{name.replace('_', '-')}-ingress",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=server.label_selector,
                policy_types=["Ingress"],
                ingress=[
                    k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                        from_=[
                            k8s.networking.v1.NetworkPolicyPeerArgs(
                                pod_selector=client.label_selector,
                            ),
                        ],
                        ports=[
                            k8s.networking.v1.NetworkPolicyPortArgs(port="http"),
                        ],
                    ),
                ],
            ),
            opts=self.default_ropts,
        )
