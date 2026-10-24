"""
projects.homelab.vaultwarden.project
====================================

This module contains the InfrastructureProject for Vaultwarden.
"""

from dataclasses import asdict
from pathlib import Path

from infralib import (
    DeploymentContext,
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from pulumi import export, ResourceOptions
from pulumi_kubernetes.core.v1 import (
    EnvVarArgs,
    EnvVarSourceArgs,
    SecretKeySelectorArgs,
)

from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabHTTPSDeploymentIngressArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    HomelabPersistentVolume,
    namespace,
    service_fqdn,
)
from ..traefik import HomelabTraefikProject


class HomelabVaultwardenProject(InfrastructureProject):
    name = "homelab.vaultwarden"
    backing_volume: HomelabBackingVolumeID = "data0"
    container_port = 8080
    image = "vaultwarden/server:1.37.1"
    data_directory = Path("/data")
    log_directory = Path("/log")
    service_name = "vaultwarden"

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
        self.service_fqdn = service_fqdn(self.dctx, self.service_name)

        deployment = HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                https_ingress=HomelabHTTPSDeploymentIngressArgs(
                    container_port=self.container_port,
                ),
                env=self._env(),
                image=self.image,
                privilege_drop_mode="pod-exec",
                volumes=[
                    HomelabContainerVolumeArgs(
                        name="data",
                        mount_path=str(self.data_directory),
                        source=HomelabContainerVolumeProvisionedSource(
                            backing_volume=self.backing_volume,
                            storage="50Gi",
                            access_modes=["ReadWriteOnce"],
                            mode="0700",
                        ),
                        read_only=False,
                    ),
                    HomelabContainerVolumeArgs(
                        name="log",
                        mount_path=str(self.log_directory),
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
        data_pv = data_v.persistent_volume
        data_pvc = data_v.persistent_volume_claim
        export(
            "data_volume",
            {
                "pv": data_pv.apply(lambda pv: asdict(pv)),
                "pvc": data_pvc.apply(lambda pvc: asdict(pvc)),
            },
        )

    def _env(self) -> list[EnvVarArgs]:
        env = {
            "DOMAIN": f"https://{self.service_fqdn}",
            "LOG_FILE": str(self.log_directory / "vaultwarden.log"),
            "ROCKET_ADDRESS": "0.0.0.0",
            "ROCKET_PORT": str(self.container_port),
            "SHOW_PASSWORD_HINT": "false",
            "SIGNUPS_ALLOWED": "false",
            "SMTP_FROM": f"vaultwarden@{self.service_fqdn}",
            "SMTP_HOST": "mail.smtp2go.com",
            "SMTP_PORT": "2525",
            "STMP_AUTH_MECHANISM": "Login",
            "STMP_SECURITY": "starttls",
            "WEBSOCKET_ENABLED": "true",
        }

        # NOTE: The smtp secret must be configured manually after the namespace
        # is provisioned. This stack can be up'd to create the namespace and other
        # resources, then the secret can be configured to allow the up to complete
        # successfully. Sign into SMTP2GO and find the SMTP user for Vaultwarden.
        #
        #     $ kubectl -n $NAMESPACE create secret generic smtp
        #     $ kubectl -n $NAMESPACE edit secret/smtp
        #
        # https://app-us.smtp2go.com/sending/smtp_users/
        secret_ref_env = [
            EnvVarArgs(
                name="SMTP_USERNAME",
                value_from=EnvVarSourceArgs(
                    secret_key_ref=SecretKeySelectorArgs(
                        name="smtp",
                        key="smtp2go_username",
                    ),
                ),
            ),
            EnvVarArgs(
                name="SMTP_PASSWORD",
                value_from=EnvVarSourceArgs(
                    secret_key_ref=SecretKeySelectorArgs(
                        name="smtp",
                        key="smtp2go_password",
                    ),
                ),
            ),
        ]
        return [
            *[
                EnvVarArgs(
                    name=k,
                    value=v,
                )
                for k, v in env.items()
            ],
            *secret_ref_env,
        ]
