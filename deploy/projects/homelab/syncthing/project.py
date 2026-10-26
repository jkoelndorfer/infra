"""
projects.homelab.syncthing.project
==================================

This module contains the project definition for the homelab.syncthing project.
"""

from dataclasses import asdict
from pathlib import Path

from pulumi import export, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import ContainerPortArgs

from infralib import (
    DeploymentContext,
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    HomelabHTTPSDeploymentIngressArgs,
    HomelabPersistentVolume,
    namespace,
)
from ..traefik import HomelabTraefikProject


class HomelabSyncthingProject(InfrastructureProject):
    """
    Project that provisions Syncthing on the homelab Kubernetes cluster.
    """

    name = "homelab.syncthing"
    service_name = "syncthing"

    image = "linuxserver/syncthing:v2.0.9-ls196"

    backing_volume_id: HomelabBackingVolumeID = "data0"
    data_directory = Path("/data")
    config_directory = Path("/config")

    container_http_port = 8384
    container_sync_port = 22000

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

    @property
    def host_sync_port(self) -> int:
        """
        Returns the host sync protocol port.
        """
        match self.dctx.target.environment:
            case Environment.DEV:
                return self.container_sync_port + 1
            case Environment.PROD:
                return self.container_sync_port
            case Environment.TEST:
                return self.container_sync_port + 2

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        self.deployment = HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                https_ingress=HomelabHTTPSDeploymentIngressArgs(
                    container_port=self.container_http_port,
                ),
                image=self.image,
                ports=[
                    ContainerPortArgs(
                        container_port=self.container_sync_port,
                        host_port=self.host_sync_port,
                        protocol="TCP",
                    ),
                    ContainerPortArgs(
                        container_port=self.container_sync_port,
                        host_port=self.host_sync_port,
                        protocol="UDP",
                    ),
                ],
                privilege_drop_mode="s6-entrypoint",
                volumes=[
                    HomelabContainerVolumeArgs(
                        name="data",
                        mount_path=str(self.data_directory),
                        source=HomelabContainerVolumeProvisionedSource(
                            backing_volume=self.backing_volume_id,
                            storage="200Gi",
                            access_modes=["ReadWriteOnce"],
                            mode="0700",
                        ),
                        read_only=False,
                    ),
                    HomelabContainerVolumeArgs(
                        name="config",
                        mount_path=str(self.config_directory),
                        source=HomelabContainerVolumeProvisionedSource(
                            backing_volume=self.backing_volume_id,
                            storage="512Mi",
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

        k8s.networking.v1.NetworkPolicy(
            "syncthing_sync",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="syncthing-sync",
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
                                port=self.container_sync_port,
                            ),
                        ],
                    ),
                ],
            ),
            opts=self.default_ropts,
        )

        self._export_vol("data")
        self._export_vol("config")

    def _export_vol(self, volume_name: str) -> None:
        v = self.deployment.volumes[volume_name]
        pv = v.persistent_volume
        pvc = v.persistent_volume_claim
        export(
            f"{volume_name}_volume",
            {
                "pv": pv.apply(lambda pv: asdict(pv)),
                "pvc": pvc.apply(lambda pvc: asdict(pvc)),
            },
        )

    @classmethod
    def data_pv(
        cls,
        dctx: DeploymentContext,
        target: DeploymentTarget,
    ) -> HomelabPersistentVolume:
        """
        Returns the Syncthing data volume for the given deployment target.
        """
        return cls._pv(dctx, target, "data")

    @classmethod
    def config_pv(
        cls,
        dctx: DeploymentContext,
        target: DeploymentTarget,
    ) -> HomelabPersistentVolume:
        """
        Returns the Syncthing config volume for the given deployment target.
        """
        return cls._pv(dctx, target, "config")

    @classmethod
    def _pv(
        cls,
        dctx: DeploymentContext,
        target: DeploymentTarget,
        volume_name: str,
    ) -> HomelabPersistentVolume:
        """
        Returns the named Syncthing volume for the given deployment target.
        """
        stack = cls.stack(target)
        o = dctx.outputs(stack)
        return HomelabPersistentVolume.from_dict(o[f"{volume_name}_volume"].value["pv"])
