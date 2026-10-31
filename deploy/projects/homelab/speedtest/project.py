"""
projects.homelab.speedtest.project
==================================

This module contains the InfrastructureProject for OpenSpeedTest.
"""

from typing import Any, cast, Sequence

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s

from ..kubernetes import (
    HomelabHTTPSDeploymentIngressArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    namespace,
)
from ..traefik import (
    HomelabTraefikProject,
    TraefikIngressRouteSpecRoute,
    TraefikMiddlewareRef,
    TraefikRouteBuilder,
)


class HomelabSpeedtestProject(InfrastructureProject):
    name = "homelab.speedtest"
    container_port = 3000
    image = "openspeedtest/latest:v2.0.6"
    service_name = "speedtest"

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

        # Required so that Traefik does not reject large uploads, which
        # causes OpenSpeedTest to report insanely high upload speeds.
        self.buffering_middleware = k8s.apiextensions.CustomResource(
            "buffering_middleware",
            api_version="traefik.io/v1alpha1",
            kind="Middleware",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="buffering",
            ),
            spec={
                "buffering": {
                    "maxRequestBodyBytes": 52428800,
                    "memRequestBodyBytes": 104857600,
                },
            },
            opts=self.default_ropts,
        )

        HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                https_ingress=HomelabHTTPSDeploymentIngressArgs(
                    container_port=self.container_port,
                    traefik_route_transform=self._traefik_route_transform,
                ),
                image=self.image,
                # NOTE: The image already runs as an unprivileged user. Its nginx
                # configuration is readable only by that user, so running under
                # the homelab service UID prevents nginx from starting.
                privilege_drop_mode=None,
                volumes=[],
            ),
            dctx=self.dctx,
            opts=self.default_ropts,
        )

    def _traefik_route_transform(
        self,
        builder: TraefikRouteBuilder,
        default_routes: Sequence[TraefikIngressRouteSpecRoute],
    ) -> list[TraefikIngressRouteSpecRoute]:
        metadata = cast(
            Output[dict[str, Any]], getattr(self.buffering_middleware, "metadata")
        )
        return [
            builder.route(
                middlewares=[
                    TraefikMiddlewareRef(
                        namespace=metadata["namespace"],
                        name=metadata["name"],
                    ),
                ],
            ),
        ]
