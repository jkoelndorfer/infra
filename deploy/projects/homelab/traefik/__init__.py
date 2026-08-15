"""
projects.homelab.traefik
========================

This module contains the homelab Traefik project.
"""

from pulumi import ResourceOptions

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import helm_release, namespace


class HomelabTraefikProject(InfrastructureProject):
    """
    Project that installs Traefik on my homelab Kubernetes cluster.
    """

    name = "homelab.traefik"
    service_name = "traefik"

    chart_oci_uri = "oci://ghcr.io/traefik/helm/traefik"
    chart_version = "41.0.0"
    chart_sha256 = "c7425a28bdc731dcb59a61cf85349463a235bf76c3c5f9f42ca8f6e2dbc62f72"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        # Traefik cannot be installed multiple times on one Kubernetes cluster,
        # so only prod is permitted here.
        return [
            DeploymentTarget(Environment.PROD, None),
        ]

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        ns_name, ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )
        helm_release(
            "traefik",
            oci_uri=self.chart_oci_uri,
            version=self.chart_version,
            sha256=self.chart_sha256,
            namespace=ns_name,
            values={},  # TODO: Add values
            opts=self.default_ropts.merge(
                ResourceOptions(import_="traefik"),
            ),
        )
