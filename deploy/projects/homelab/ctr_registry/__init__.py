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
    HomelabService,
    namespace,
)
from ..traefik import (
    default_route,
    default_host_match,
    HomelabTraefikProject,
    TraefikIngressRouteSpecRoute,
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
                    hostname="ctr-registry-rw",
                    san_hostnames=["ctr-registry-ro"],
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

    @classmethod
    def _traefik_route_transform(
        cls,
        service: HomelabService,
        default_routes: Sequence[TraefikRouteSpec],
    ) -> list[TraefikRouteSpec]:
        pass
