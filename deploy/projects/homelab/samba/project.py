"""
projects.homelab.samba.project
==============================

This module contains the InfrastructureProject for Samba, which serves SMB file
shares on the Kubernetes host's port 445. The image's configuration is documented at
[1], and smb.conf at [2].

The image reads /etc/samba/smb.conf as given, and creates the accounts listed in
/etc/samba/users.conf, setting their passwords, every time it starts [3]. Samba's own
account database is not persisted, so users.conf is the only source of accounts.

The image runs as root, because it creates Unix accounts and Samba switches to them
for file access.

[1]: https://github.com/dockur/samba
[2]: https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html
[3]: https://github.com/dockur/samba/blob/v4.23.10-r0/samba.sh
"""

import hashlib
from pathlib import PurePosixPath

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import (
    ContainerPortArgs,
    KeyToPathArgs,
    SecretVolumeSourceArgs,
)

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import (
    HomelabContainerSecretVolumeArgs,
    HomelabContainerVolumeArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    namespace,
    uid_gid,
)
from .scans import provision_scan_share
from .share import SambaAccount, smb_conf, users_conf


class HomelabSambaProject(InfrastructureProject):
    """
    Project that provisions Samba on the homelab Kubernetes cluster.
    """

    name = "homelab.samba"
    service_name = "samba"

    image = "dockurr/samba:4.23.10"

    config_directory = PurePosixPath("/etc/samba")

    # The config secret's keys, and the files in config_directory they are mounted
    # as. Keys are limited to letters, digits, and underscores, so that they can be
    # read with templates such as kubectl's jsonpath.
    config_files = {
        "smb_conf": "smb.conf",
        "users_conf": "users.conf",
    }

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        # Samba binds a host port, so a second environment would collide with this
        # one if scheduled on the same node.
        return [DeploymentTarget(Environment.PROD, None)]

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        smb_port = self.dctx.config.homelab.network.ports.smb

        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        shares = [provision_scan_share(self.dctx, self.service_name)]

        accounts: dict[str, SambaAccount] = {}
        for share in shares:
            for account in share.accounts:
                if accounts.setdefault(account.name, account) is not account:
                    raise ValueError(f"account {account.name!r} is defined twice")

        # Every account's primary group is the service's group, which the shares'
        # volumes are owned by.
        group = self.service_name
        gid = uid_gid(self.dctx.target.environment, self.service_name)

        config_secret = self._config_secret(
            smb_conf(shares, group),
            users_conf(list(accounts.values()), group, gid),
        )

        k8s.core.v1.Secret(
            "accounts",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="samba-accounts",
            ),
            string_data={a.name: a.password for a in accounts.values()},
            opts=self.default_ropts,
        )

        self.deployment = HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                image=self.image,
                ports=[
                    ContainerPortArgs(
                        container_port=smb_port,
                        host_port=smb_port,
                        protocol="TCP",
                    ),
                ],
                privilege_drop_mode=None,
                volumes=[
                    HomelabContainerVolumeArgs(
                        name=share.name,
                        mount_path=str(share.path),
                        source=share.volume,
                        read_only=False,
                    )
                    for share in shares
                ],
                secret_volumes=[
                    HomelabContainerSecretVolumeArgs(
                        name="config",
                        mount_path=str(self.config_directory),
                        secret=SecretVolumeSourceArgs(
                            secret_name=config_secret.metadata["name"],
                            default_mode=0o400,
                            items=[
                                KeyToPathArgs(key=key, path=path)
                                for key, path in self.config_files.items()
                            ],
                        ),
                    ),
                ],
            ),
            dctx=self.dctx,
            opts=self.default_ropts,
        )

        # Selecting the pod isolates it, so this is all the ingress it accepts.
        # Clients arrive through the host port, which forwards them to the pod's
        # port with their source address intact; the router's firewall decides
        # which networks may reach it.
        k8s.networking.v1.NetworkPolicy(
            "smb",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="smb",
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=self.deployment.label_selector,
                policy_types=["Ingress"],
                ingress=[
                    k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                        from_=[
                            k8s.networking.v1.NetworkPolicyPeerArgs(
                                ip_block=k8s.networking.v1.IPBlockArgs(
                                    cidr="0.0.0.0/0"
                                ),
                            )
                        ],
                        ports=[
                            k8s.networking.v1.NetworkPolicyPortArgs(
                                port=smb_port,
                                protocol="TCP",
                            ),
                        ],
                    ),
                ],
            ),
            opts=self.default_ropts,
        )

    def _config_secret(
        self,
        smb_conf: str,
        users_conf: Output[str],
    ) -> k8s.core.v1.Secret:
        """
        Provisions the secret holding smb.conf and users.conf. They are kept together
        because the image reads both from the same directory.
        """
        data = users_conf.apply(
            lambda u: {"smb_conf": smb_conf, "users_conf": u},
        )

        # The image reads its configuration only at startup. Autonaming is
        # verbatim, so a content hash in the name is what rolls the pod on a
        # change.
        def name(d: dict[str, str]) -> str:
            digest = hashlib.sha256()
            for k in sorted(d):
                digest.update(f"{k}\0{d[k]}\0".encode())
            return f"{self.service_name}-config-{digest.hexdigest()[:8]}"

        return k8s.core.v1.Secret(
            "config",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name=data.apply(name),
            ),
            string_data=data,
            opts=self.default_ropts,
        )
