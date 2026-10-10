"""
projects.homelab.ctr_registry
=============================

This module contains the homelab container registry project.
"""

from typing import Sequence

from pulumi import ResourceOptions

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import (
    HomelabHTTPSDeploymentIngressArgs,
    HomelabBackingVolume,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
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


class HomelabContainerRegistryProject(InfrastructureProject):
    """
    Project that installs a container registry on the homelab Kubernetes cluster.
    """

    name = "homelab.ctr_registry"
    service_name = "registry"

    backing_volume: HomelabBackingVolume = "data0"
    image = "docker.io/registry:3.0.0"
    container_port = 5000

    # Hostname permitting read-write access to the container registry.
    rw_hostname = "ctr-registry-rw"

    # Hostname permitting read-only access to the container registry.
    ro_hostname = "ctr-registry-ro"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [
            HomelabTraefikProject.stack(DeploymentTarget(Environment.PROD, None)),
        ]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.DEV, None),
            DeploymentTarget(Environment.PROD, None),
        ]

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                https_ingress=HomelabHTTPSDeploymentIngressArgs(
                    container_port=self.container_port,
                    hostname=self.rw_hostname,
                    san_hostnames=[self.ro_hostname],
                    traefik_route_transform=self._traefik_route_transform,
                ),
                image=self.image,
                privilege_drop_mode="pod-exec",
                volumes=[
                    HomelabContainerVolumeArgs(
                        name="data",
                        mount_path="/var/lib/registry",
                        source=HomelabContainerVolumeProvisionedSource(
                            backing_volume=self.backing_volume,
                            storage="50Gi",
                            access_modes=["ReadWriteOnce"],
                            mode="0744",
                        ),
                        read_only=False,
                    )
                ],
            ),
            dctx=self.dctx,
            opts=self.default_ropts,
        )

    def _traefik_route_transform(
        self,
        builder: TraefikRouteBuilder,
        default_routes: Sequence[TraefikIngressRouteSpecRoute],
    ) -> list[TraefikIngressRouteSpecRoute]:
        # TODO: Create rw-middleware.
        rw_middlewares = [
            TraefikMiddlewareRef(
                namespace=self.ns_name,
                name="TODO",
            ),
        ]
        rw_fqdn = f"{self.rw_hostname}.{builder.homelab_service.domain}"

        # TODO: Create ro-middleware.
        ro_middlewares = [
            TraefikMiddlewareRef(
                namespace=self.ns_name,
                name="TODO",
            ),
        ]
        ro_fqdn = f"{self.ro_hostname}.{builder.homelab_service.domain}"

        # TODO: Configure deny middleware
        deny_middlewares = [
            TraefikMiddlewareRef(
                namespace=self.ns_name,
                name="TODO",
            ),
        ]

        return [
            builder.route(
                match=f"Host(`{rw_fqdn}`)",
                middlewares=rw_middlewares,
                priority=110,
            ),
            builder.route(
                match=f"Host(`{ro_fqdn}`) && ( METHOD(`GET`) || METHOD(`HEAD`) || METHOD(`TRACE`) )",
                priority=101,
                middlewares=ro_middlewares,
            ),
            builder.route(
                match=f"Host(`{ro_fqdn}`)",
                priority=100,
                middlewares=deny_middlewares,
            ),
        ]
