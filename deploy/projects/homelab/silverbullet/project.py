"""
projects.homelab.silverbullet.project
=====================================

This module contains the InfrastructureProject for SilverBullet, a notes app that
keeps its notes as Markdown files [1]. Its image and configuration are documented at
[2] and [3].

SilverBullet runs in its default multi-space mode, in which its data folder holds the
server's configuration, accounts, and spaces, all managed in its web dashboard [4].
The single-space mode, configured with environment variables such as SB_USER, is
deprecated [3].

NOTE: With an empty data folder, SilverBullet starts in setup mode, in which anyone
who can reach it creates the first administrator account [4]. Complete the setup
right after the first deployment of each environment.

NOTE: SilverBullet runs the data folder's CONTAINER_BOOT.md as a shell script when
the container starts [5]. Anyone who can write that file can run commands in the
container. Keep spaces out of the data folder's root, so that editing notes cannot
create it.

[1]: https://silverbullet.md/
[2]: https://docs.silverbullet.md/Install/Docker
[3]: https://docs.silverbullet.md/Install/Configuration
[4]: https://docs.silverbullet.md/Dashboard
[5]: https://github.com/silverbulletmd/silverbullet/blob/2.12.1/docker-entrypoint.sh
"""

from dataclasses import asdict
from pathlib import PurePosixPath

from infralib import (
    DeploymentContext,
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from pulumi import export, ResourceOptions
from pulumi_kubernetes.core.v1 import EnvVarArgs

from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabHTTPSDeploymentIngressArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    HomelabPersistentVolume,
    namespace,
)
from ..traefik import HomelabTraefikProject


class HomelabSilverBulletProject(InfrastructureProject):
    name = "homelab.silverbullet"
    backing_volume: HomelabBackingVolumeID = "data0"
    container_port = 3000
    data_directory = PurePosixPath("/data")
    service_name = "silverbullet"

    # The slim variant leaves out Chromium, which only the Runtime API uses.
    image = "ghcr.io/silverbulletmd/silverbullet:2.12.1-slim"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [HomelabTraefikProject.stack(DeploymentTarget(Environment.PROD, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(e, None) for e in [Environment.DEV, Environment.PROD]]

    @classmethod
    def data_pv(
        cls,
        dctx: DeploymentContext,
        target: DeploymentTarget,
    ) -> HomelabPersistentVolume:
        outputs = dctx.outputs(cls.stack(target))
        pv_dict = outputs["data_volume"].value["pv"]
        return HomelabPersistentVolume.from_dict(pv_dict)

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        deployment = HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                https_ingress=HomelabHTTPSDeploymentIngressArgs(
                    container_port=self.container_port,
                    hostname="notes",
                ),
                env=[
                    EnvVarArgs(name="SB_FOLDER", value=str(self.data_directory)),
                    EnvVarArgs(name="SB_PORT", value=str(self.container_port)),
                ],
                image=self.image,
                # The image's entrypoint runs the server directly when it starts
                # as a user other than root, so PUID and PGID are not needed.
                privilege_drop_mode="pod-exec",
                volumes=[
                    HomelabContainerVolumeArgs(
                        name="data",
                        mount_path=str(self.data_directory),
                        source=HomelabContainerVolumeProvisionedSource(
                            backing_volume=self.backing_volume,
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

        data_v = deployment.volumes["data"]
        export(
            "data_volume",
            {
                "pv": data_v.persistent_volume.apply(lambda pv: asdict(pv)),
                "pvc": data_v.persistent_volume_claim.apply(lambda pvc: asdict(pvc)),
            },
        )
