"""
projects.homelab.monitoring.project
===================================

This module contains the InfrastructureProject for homelab monitoring: VictoriaMetrics
stores metrics, VictoriaLogs stores logs, and Grafana visualizes both. The SNMP
exporter collects metrics from the router and switches. The node and smartctl
exporters collect metrics from the Kubernetes host, and the health of its disks.
Fluent Bit collects the logs of every pod.
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
from .fluent_bit import FluentBitArgs, provision_fluent_bit
from .grafana import GrafanaArgs, provision_grafana
from .node_exporter import NodeExporterArgs, provision_node_exporter
from .smartctl_exporter import SmartctlExporterArgs, provision_smartctl_exporter
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
from .victorialogs import (
    VictoriaLogsArgs,
    VictoriaLogsSyslogArgs,
    provision_victorialogs,
    router_syslog_source,
    switch_syslog_source,
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

        node_exporter = provision_node_exporter(
            self.dctx,
            NodeExporterArgs(
                namespace=self.ns_name,
                host_address=networking.kubernetes_host,
            ),
            self.default_ropts,
        )
        smartctl_exporter = provision_smartctl_exporter(
            SmartctlExporterArgs(namespace=self.ns_name),
            self.default_ropts,
        )

        vl = provision_victorialogs(
            self.dctx,
            VictoriaLogsArgs(namespace=self.ns_name, syslog=self._syslog_args()),
            self.default_ropts,
        )
        fluent_bit = provision_fluent_bit(
            self.dctx,
            FluentBitArgs(namespace=self.ns_name, victorialogs=vl),
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
                    node_exporter.scrape_job,
                    smartctl_exporter.scrape_job,
                    vl.scrape_job,
                    fluent_bit.scrape_job,
                ],
            ),
            self.default_ropts,
        )

        grafana = provision_grafana(
            self.dctx,
            GrafanaArgs(
                namespace=self.ns_name,
                victoriametrics=vm,
                victorialogs=vl,
            ),
            self.default_ropts,
        )

        vm_pods = vm.deployment.label_selector
        self._provision_ingress_policy(
            "victoriametrics",
            vm.deployment.label_selector,
            [grafana.deployment.label_selector],
        )
        self._provision_ingress_policy(
            "snmp_exporter", snmp_exporter.deployment.label_selector, [vm_pods]
        )
        # The node exporter runs in the host's network namespace, where no policy
        # applies to it. It requires authentication instead.
        self._provision_ingress_policy(
            "smartctl_exporter",
            smartctl_exporter.daemon_set.label_selector,
            [vm_pods],
        )
        self._provision_ingress_policy(
            "victorialogs",
            vl.deployment.label_selector,
            [
                grafana.deployment.label_selector,
                fluent_bit.daemon_set.label_selector,
                vm_pods,
            ],
        )
        self._provision_ingress_policy(
            "fluent_bit", fluent_bit.daemon_set.label_selector, [vm_pods]
        )

    def _syslog_args(self) -> VictoriaLogsSyslogArgs | None:
        """
        Returns how VictoriaLogs receives the network devices' syslog. Only prod
        receives it, because the host port can be taken only once on the host.
        """
        if self.dctx.target.environment != Environment.PROD:
            return None

        networking = self.dctx.config.homelab.network
        return VictoriaLogsSyslogArgs(
            host_port=networking.ports.syslog,
            sources=[
                switch_syslog_source(networking),
                router_syslog_source(networking),
            ],
        )

    def _provision_ingress_policy(
        self,
        name: str,
        server: k8s.meta.v1.LabelSelectorArgs,
        clients: list[k8s.meta.v1.LabelSelectorArgs],
    ) -> None:
        """
        Provisions a policy that permits only the pods that clients select to reach
        the HTTP port of the pods that server selects. Selecting the server's pods
        denies all other ingress to them.
        """
        k8s.networking.v1.NetworkPolicy(
            f"{name}_ingress",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name=f"{name.replace('_', '-')}-ingress",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=server,
                policy_types=["Ingress"],
                ingress=[
                    k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                        from_=[
                            k8s.networking.v1.NetworkPolicyPeerArgs(
                                pod_selector=client,
                            )
                            for client in clients
                        ],
                        ports=[
                            k8s.networking.v1.NetworkPolicyPortArgs(port="http"),
                        ],
                    ),
                ],
            ),
            opts=self.default_ropts,
        )
