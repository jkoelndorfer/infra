"""
projects.homelab.monitoring.project
===================================

This module contains the InfrastructureProject for homelab monitoring: VictoriaMetrics
stores metrics, and Grafana visualizes them.
"""

from pulumi import ResourceOptions
import pulumi_kubernetes as k8s

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import namespace
from ..traefik import HomelabTraefikProject
from .grafana import GrafanaArgs, GrafanaResult, provision_grafana
from .victoriametrics import (
    ScrapeJob,
    VictoriaMetricsArgs,
    VictoriaMetricsResult,
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

        vm = provision_victoriametrics(
            self.dctx,
            VictoriaMetricsArgs(
                namespace=self.ns_name,
                scrape_jobs=[
                    ScrapeJob(
                        name="traefik",
                        targets=[HomelabTraefikProject.metrics_target(self.dctx)],
                    ),
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

        self._provision_victoriametrics_ingress_policy(vm, grafana)

    def _provision_victoriametrics_ingress_policy(
        self,
        vm: VictoriaMetricsResult,
        grafana: GrafanaResult,
    ) -> None:
        """
        Provisions a policy that permits only Grafana to reach VictoriaMetrics.
        Selecting the pods denies all other ingress to them.
        """
        k8s.networking.v1.NetworkPolicy(
            "victoriametrics_ingress",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="victoriametrics-ingress",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=vm.deployment.label_selector,
                policy_types=["Ingress"],
                ingress=[
                    k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                        from_=[
                            k8s.networking.v1.NetworkPolicyPeerArgs(
                                pod_selector=grafana.deployment.label_selector,
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
