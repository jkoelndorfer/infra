"""
projects.homelab.forgejo.project
================================

This module contains the InfrastructureProject for Forgejo, a self-hosted software
forge [1]. It runs the rootless container image [2], which keeps all of its state,
including its configuration file, in the data folder.

The container's entrypoint writes app.ini on first start and, on every start,
applies the FORGEJO__<SECTION>__<KEY> environment variables to it [3][4]. Settings
made here therefore override the file, and the rest of the file is Forgejo's own.

Every page and repository requires signing in, including over Git. Git is served
over HTTPS only. Forgejo's built-in SSH server is turned off. Forgejo
uses SQLite, stored in the data folder.

NOTE: Registration is disabled and the install wizard is locked, so the first
deployment of each environment has no users. Create the administrator account
after it starts:

    $ kubectl -n $NAMESPACE exec deploy/forgejo -- \\
        forgejo admin user create --admin --username $USERNAME --email $EMAIL \\
        --random-password

NOTE: The SECRET_KEY generated here encrypts secrets in the database, such as
two-factor authentication keys [5]. It must stay with the database: restoring the
data folder into a stack with a different key makes those secrets unreadable.

NOTE: The smtp secret must be configured manually after the namespace is
provisioned, as with Vaultwarden. Sign into SMTP2GO and find the SMTP user for
Forgejo.

    $ kubectl -n $NAMESPACE create secret generic smtp \\
        --from-literal=smtp2go_username=... --from-literal=smtp2go_password=...

[1]: https://forgejo.org/
[2]: https://forgejo.org/docs/latest/admin/installation/docker/
[3]: https://codeberg.org/forgejo/forgejo/src/tag/v17.0.2/docker/rootless/usr/local/bin/docker-setup.sh
[4]: https://forgejo.org/docs/latest/admin/config-cheat-sheet/
[5]: https://forgejo.org/docs/latest/admin/config-cheat-sheet/#security-security
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

from pulumi import export, Input, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import (
    EnvVarArgs,
    EnvVarSourceArgs,
    SecretKeySelectorArgs,
)
import pulumi_random as random

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


class HomelabForgejoProject(InfrastructureProject):
    name = "homelab.forgejo"
    backing_volume: HomelabBackingVolumeID = "data0"
    container_port = 3000
    # The image's GITEA_WORK_DIR.
    data_directory = PurePosixPath("/var/lib/gitea")
    hostname = "git"
    service_name = "forgejo"

    image = "codeberg.org/forgejo/forgejo:17.0.2-rootless"

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
        self.service_fqdn = service_fqdn(self.dctx, self.hostname)

        secret_key = random.RandomPassword(
            "secret_key",
            length=64,
            special=False,
            opts=ResourceOptions(provider=self.dctx.provider_factory.random_provider()),
        )
        self.secrets = k8s.core.v1.Secret(
            "secrets",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name=f"{self.service_name}-secrets",
            ),
            string_data={"secret_key": secret_key.result},
            opts=self.default_ropts,
        )

        deployment = HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                https_ingress=HomelabHTTPSDeploymentIngressArgs(
                    container_port=self.container_port,
                    hostname=self.hostname,
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
                            storage="100Gi",
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

    def _env(self) -> list[EnvVarArgs]:
        settings = {
            "server": {
                "DOMAIN": self.service_fqdn,
                "ROOT_URL": f"https://{self.service_fqdn}/",
                "HTTP_PORT": str(self.container_port),
                "DISABLE_SSH": "true",
                "START_SSH_SERVER": "false",
                "LFS_START_SERVER": "true",
            },
            "database": {
                "DB_TYPE": "sqlite3",
            },
            "security": {
                "INSTALL_LOCK": "true",
            },
            "service": {
                "DISABLE_REGISTRATION": "true",
                "REQUIRE_SIGNIN_VIEW": "true",
            },
            # Actions stays off until there is a runner to run its jobs.
            "actions": {
                "ENABLED": "false",
            },
            "packages": {
                "ENABLED": "true",
            },
            "mailer": {
                "ENABLED": "true",
                "PROTOCOL": "smtp+starttls",
                "SMTP_ADDR": "mail.smtp2go.com",
                "SMTP_PORT": "2525",
                "FROM": f"forgejo@{self.service_fqdn}",
            },
        }
        secret_settings: dict[tuple[str, str], tuple[Input[str], str]] = {
            ("security", "SECRET_KEY"): (self.secrets.metadata["name"], "secret_key"),
            ("mailer", "USER"): ("smtp", "smtp2go_username"),
            ("mailer", "PASSWD"): ("smtp", "smtp2go_password"),
        }

        return [
            # The image writes RUN_USER from USER when it creates app.ini, and
            # Forgejo falls back to USER for its own name, because the pod's UID
            # has no passwd entry. They must match, or Forgejo refuses to start.
            EnvVarArgs(name="USER", value="git"),
            *[
                EnvVarArgs(name=f"FORGEJO__{section}__{key}", value=value)
                for section, values in settings.items()
                for key, value in values.items()
            ],
            *[
                EnvVarArgs(
                    name=f"FORGEJO__{section}__{key}",
                    value_from=EnvVarSourceArgs(
                        secret_key_ref=SecretKeySelectorArgs(
                            name=secret_name,
                            key=secret_key,
                        ),
                    ),
                )
                for (section, key), (secret_name, secret_key) in secret_settings.items()
            ],
        ]
