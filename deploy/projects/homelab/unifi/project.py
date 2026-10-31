"""
projects.homelab.unifi.project
==============================

This module contains the InfrastructureProject for the UniFi Controller.

The ports used by the controller are documented at [1].

[1]: https://github.com/linuxserver-archive/docker-unifi-controller?tab=readme-ov-file#parameters
"""

from pathlib import Path
from typing import Any, cast, Sequence

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import ContainerPortArgs

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabHTTPSDeploymentIngressArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    namespace,
)
from ..traefik import (
    HomelabTraefikProject,
    TraefikIngressRouteSpecRoute,
    TraefikRouteBuilder,
    TraefikServiceRef,
)


class HomelabUnifiProject(InfrastructureProject):
    """
    Project that provisions the UniFi Controller on the homelab Kubernetes cluster.
    """

    name = "homelab.unifi"
    service_name = "unifi"

    image = "linuxserver/unifi-controller:7.3.76-ls174"

    backing_volume_id: HomelabBackingVolumeID = "data0"
    config_directory = Path("/config")

    web_port = 8443
    device_port = 8080
    ap_discovery_port = 10001
    stun_port = 3478

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [HomelabTraefikProject.stack(DeploymentTarget(Environment.PROD, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        # UniFi devices expect fixed host ports, so a second environment would
        # collide with this one if scheduled on the same node.
        return [DeploymentTarget(Environment.PROD, None)]

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)

        # NOTE: The legacy homelab_unifi Terragrunt unit owns resources with the
        # same names, and its selector labels differ. Destroy that unit before
        # the first up of this stack. Devices cannot reach the controller until
        # this stack is up.
        #
        # The legacy unit stored its data in a differently named directory, and
        # its volume is retained when destroyed. Move the data on the node before
        # the first up, or the controller starts empty and devices must be
        # adopted again.
        #
        #     $ cd $BACKING_VOLUME_PATH/prod-unifi
        #     $ sudo mv unifi-config config
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        # The controller serves its web interface over HTTPS with a self-signed
        # certificate, which Traefik must be told to accept.
        self.insecure_transport = k8s.apiextensions.CustomResource(
            "insecure_transport",
            api_version="traefik.io/v1alpha1",
            kind="ServersTransport",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="insecure-transport",
            ),
            spec={
                "insecureSkipVerify": True,
            },
            opts=self.default_ropts,
        )

        self.deployment = HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                https_ingress=HomelabHTTPSDeploymentIngressArgs(
                    container_port=self.web_port,
                    traefik_route_transform=self._traefik_route_transform,
                ),
                image=self.image,
                ports=[
                    ContainerPortArgs(
                        container_port=self.device_port,
                        host_port=self.device_port,
                        protocol="TCP",
                    ),
                    ContainerPortArgs(
                        container_port=self.ap_discovery_port,
                        host_port=self.ap_discovery_port,
                        protocol="UDP",
                    ),
                    ContainerPortArgs(
                        container_port=self.stun_port,
                        host_port=self.stun_port,
                        protocol="UDP",
                    ),
                ],
                privilege_drop_mode="s6-entrypoint",
                volumes=[
                    HomelabContainerVolumeArgs(
                        name="config",
                        mount_path=str(self.config_directory),
                        source=HomelabContainerVolumeProvisionedSource(
                            backing_volume=self.backing_volume_id,
                            storage="10Gi",
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
        # otherwise drop traffic from devices arriving through the host ports.
        k8s.networking.v1.NetworkPolicy(
            "unifi_devices",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="unifi-devices",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=self.deployment.label_selector,
                ingress=[
                    k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                        from_=[
                            k8s.networking.v1.NetworkPolicyPeerArgs(
                                # TODO: Implement IP constraints.
                                ip_block=k8s.networking.v1.IPBlockArgs(
                                    cidr="0.0.0.0/0"
                                ),
                            )
                        ],
                        ports=[
                            k8s.networking.v1.NetworkPolicyPortArgs(
                                port=self.device_port,
                                protocol="TCP",
                            ),
                            k8s.networking.v1.NetworkPolicyPortArgs(
                                port=self.ap_discovery_port,
                                protocol="UDP",
                            ),
                            k8s.networking.v1.NetworkPolicyPortArgs(
                                port=self.stun_port,
                                protocol="UDP",
                            ),
                        ],
                    ),
                ],
            ),
            opts=self.default_ropts,
        )

    def _traefik_route_transform(
        self,
        builder: TraefikRouteBuilder,
        default_routes: Sequence[TraefikIngressRouteSpecRoute],
    ) -> list[TraefikIngressRouteSpecRoute]:
        metadata = cast(
            Output[dict[str, Any]], getattr(self.insecure_transport, "metadata")
        )
        return [
            builder.route(
                services=[
                    TraefikServiceRef(
                        name=builder.homelab_service.service_name,
                        port=builder.homelab_service.container_port,
                        scheme="https",
                        servers_transport=metadata["name"],
                    ),
                ],
            ),
        ]
