"""
projects.homelab.argo_workflows.project
=======================================

This module contains the InfrastructureProject for Argo Workflows.
"""

from typing import Any

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from pulumi import ResourceOptions
import pulumi_kubernetes as k8s

from ..kubernetes import helm_release, namespace


class HomelabArgoWorkflowsProject(InfrastructureProject):
    name = "homelab.argo_workflows"
    service_name = "argo-workflows"

    chart_oci_uri = "oci://ghcr.io/argoproj/argo-helm/argo-workflows"
    chart_version = "2.0.14"
    chart_sha256 = "31b3f94d0ca3b6d3bd8d2b795d6f54c2edb3622867b10a52b0039f62a3ac4cd1"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(Environment.PROD, None)]

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )
        helm_release(
            "argo_workflows",
            oci_uri=self.chart_oci_uri,
            version=self.chart_version,
            sha256=self.chart_sha256,
            namespace=self.ns_name,
            values=self._chart_values(),
            opts=self.default_ropts,
            release_name=self.service_name,
        )
        self._provision_deny_ingress_policy()

    def _chart_values(self) -> dict[str, Any]:
        # See:
        #   * https://github.com/argoproj/argo-helm/blob/argo-workflows-2.0.14/charts/argo-workflows/README.md
        #   * https://github.com/argoproj/argo-helm/blob/argo-workflows-2.0.14/charts/argo-workflows/values.yaml
        return {
            "namespaceOverride": self.ns_name,
            # Keeps resource names independent of the Helm release name.
            "fullnameOverride": self.service_name,
            "controller": {
                "workflowWorkers": 2,
                "workflowTTLWorkers": 2,
                "podCleanupWorkers": 1,
                "cronWorkflowWorkers": 2,
            },
            # The controller runs CronWorkflows without the server. The server's
            # service account can read secrets and create workflows in every
            # namespace, so it isn't deployed. To use the UI, run the following
            # on a workstation, which uses the workstation's kubeconfig:
            #
            #     $ argo server --auth-mode=server
            "server": {
                "enabled": False,
            },
        }

    def _provision_deny_ingress_policy(self) -> None:
        """
        Provisions a policy that denies all ingress to pods in this namespace.

        Nothing in this namespace needs to receive traffic now that the server
        isn't deployed.
        """
        k8s.networking.v1.NetworkPolicy(
            "deny_all_ingress",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="deny-all-ingress",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=k8s.meta.v1.LabelSelectorArgs(),
                policy_types=["Ingress"],
            ),
            opts=self.default_ropts,
        )
