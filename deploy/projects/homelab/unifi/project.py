"""
projects.homelab.unifi.project
==============================

This module contains the InfrastructureProject for the UniFi Controller.

The controller is the UniFi Network Application [1], which stores its data in
a MongoDB database that `database` provisions. The ports it uses are documented
at [1].

[1]: https://github.com/linuxserver/docker-unifi-network-application#parameters
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
from .database import UnifiDatabaseArgs, provision_database


class HomelabUnifiProject(InfrastructureProject):
    """
    Project that provisions the UniFi Controller on the homelab Kubernetes cluster.
    """

    name = "homelab.unifi"
    service_name = "unifi"

    image = "linuxserver/unifi-network-application:10.6.109-ls153"

    backing_volume_id: HomelabBackingVolumeID = "data0"
    config_directory = Path("/config")

    web_port = 8443

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
        ports = self.dctx.config.homelab.network.ports

        # NOTE: The legacy homelab_unifi Terragrunt unit owns resources with the
        # same names, and its selector labels differ. Destroy that unit before
        # the first up of this stack. Devices cannot reach the controller until
        # this stack is up.
        #
        # NOTE: The UniFi Network Application cannot read the data of the
        # unifi-controller image it replaced, which ran MongoDB inside its own
        # container. Its settings move over through a backup instead:
        #
        # 1. In the old controller, download a backup from Settings > System >
        #    Backups, before the first up of this version of the stack.
        # 2. Once this stack is up, choose to restore from a backup in the
        #    setup wizard, and upload it.
        #
        # Devices keep reporting to the same host ports, so they do not need to
        # be adopted again. The old controller's data remains on the node in
        # $BACKING_VOLUME_PATH/prod-unifi/config; delete it once the restore
        # has been verified.
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

        self.database = provision_database(
            self.dctx,
            UnifiDatabaseArgs(
                namespace=self.ns_name,
                client_label_selector=k8s.meta.v1.LabelSelectorArgs(
                    match_labels={"service-name": self.service_name},
                ),
            ),
            self.default_ropts,
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
                env=self.database.client_env,
                ports=[
                    ContainerPortArgs(
                        container_port=ports.unifi_device,
                        host_port=ports.unifi_device,
                        protocol="TCP",
                    ),
                    ContainerPortArgs(
                        container_port=ports.unifi_ap_discovery,
                        host_port=ports.unifi_ap_discovery,
                        protocol="UDP",
                    ),
                    ContainerPortArgs(
                        container_port=ports.unifi_stun,
                        host_port=ports.unifi_stun,
                        protocol="UDP",
                    ),
                ],
                privilege_drop_mode="s6-entrypoint",
                volumes=[
                    # The application reads its database settings from the
                    # environment only on its first start, when /config is
                    # empty. This volume is named differently from the one the
                    # unifi-controller image used, whose configuration points
                    # at that image's own database.
                    HomelabContainerVolumeArgs(
                        name="data",
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
                                port=ports.unifi_device,
                                protocol="TCP",
                            ),
                            k8s.networking.v1.NetworkPolicyPortArgs(
                                port=ports.unifi_ap_discovery,
                                protocol="UDP",
                            ),
                            k8s.networking.v1.NetworkPolicyPortArgs(
                                port=ports.unifi_stun,
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
