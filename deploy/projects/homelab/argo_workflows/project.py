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
from pulumi_random import RandomPasswordArgs

from ..kubernetes import helm_release, namespace
from ..traefik import (
    HomelabTraefikProject,
    TraefikHTTPBasicAuthMiddleware,
    TraefikHTTPBasicAuthMiddlewareArgs,
    TraefikHTTPBasicAuthSecretArgs,
)


class HomelabArgoWorkflowsProject(InfrastructureProject):
    name = "homelab.argo_workflows"
    service_name = "argo-workflows"

    chart_oci_uri = "oci://ghcr.io/argoproj/argo-helm/argo-workflows"
    chart_version = "0.45.26"
    chart_sha256 = "878fcbe964b92cf603b70de6d4eceff333ec1b1a288875ee959645262f8e6e7d"

    server_service_port_name = "argo-workflows-server"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [HomelabTraefikProject.stack(DeploymentTarget(Environment.PROD, None))]

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
        )

    def _chart_values(self) -> dict[str, Any]:
        # See:
        #   * https://github.com/argoproj/argo-helm/blob/7bf2ed4315b88cdd9438695b443de504f4ee9a66/charts/argo-workflows/README.md
        #   * https://github.com/argoproj/argo-helm/blob/7bf2ed4315b88cdd9438695b443de504f4ee9a66/charts/argo-workflows/values.yaml
        return {
            "namespaceOverride": self.ns_name,
            "controller": {
                "workflowWorkers": 2,
                "workflowTTLWorkers": 2,
                "podCleanupWorkers": 1,
                "cronWorkflowWorkers": 2,
            },
            "server": {
                "authModes": [
                    "server",
                ],
                "servicePortName": self.server_service_port_name,
            },
        }

    def _provision_traefik_ingress(self) -> None:
        self.traefik_middleware = TraefikHTTPBasicAuthMiddleware(
            "auth",
            TraefikHTTPBasicAuthMiddlewareArgs(
                namespace=self.ns_name,
                name="auth",
                secret=TraefikHTTPBasicAuthSecretArgs(
                    username="argo-workflows",
                    password_args=RandomPasswordArgs(
                        length=32,
                        lower=True,
                        upper=True,
                        number=True,
                        special=False,
                    ),
                ),
            ),
            self.dctx,
            opts=self.default_ropts,
        )
