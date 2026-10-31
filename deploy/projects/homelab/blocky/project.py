"""
projects.homelab.blocky.project
===============================

This module contains the InfrastructureProject for Blocky, a DNS ad blocker.

The Blocky configuration is documented at [1].

[1]: https://0xerr0r.github.io/blocky/latest/configuration/
"""

import hashlib
import json
from pathlib import PurePosixPath
from typing import Any

from pulumi import ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import (
    ConfigMapVolumeSourceArgs,
    ContainerPortArgs,
    EnvVarArgs,
)

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import (
    HomelabContainerConfigMapVolumeArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    namespace,
)


class HomelabBlockyProject(InfrastructureProject):
    """
    Project that provisions Blocky on the homelab Kubernetes cluster.
    """

    name = "homelab.blocky"
    service_name = "blocky"

    image = "spx01/blocky:v0.32.1"

    config_directory = PurePosixPath("/config")
    config_file_name = "main.yml"

    container_dns_port = 5353
    host_dns_port = 53

    # FIXME: Set the router IP in a repo-level configuration file accessible by
    # both Pulumi and pyinfra.
    upstream_dns_servers = ["192.168.192.1"]
    ad_denylists = ["https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"]

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        # Blocky binds a host port, so a second environment would collide with
        # this one if scheduled on the same node.
        return [DeploymentTarget(Environment.PROD, None)]

    def pulumi_program(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)

        # NOTE: The legacy homelab_blocky Terragrunt unit owns resources with the
        # same names, and its selector labels differ. Destroy that unit before
        # the first up of this stack. LAN clients using Blocky lose DNS until
        # this stack is up.
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )

        # YAML is a superset of JSON, so Blocky can read this as its YAML config.
        config = json.dumps(self._config(), indent=2, sort_keys=True)

        # Blocky reads its configuration only at startup. Autonaming is verbatim,
        # so a content hash in the name is what rolls the pod on a config change.
        config_hash = hashlib.sha256(config.encode()).hexdigest()[:8]
        config_map = k8s.core.v1.ConfigMap(
            "config",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name=f"{self.service_name}-{config_hash}",
            ),
            data={self.config_file_name: config},
            opts=self.default_ropts,
        )

        HomelabKubernetesDeployment(
            name="deployment",
            args=HomelabKubernetesDeploymentArgs(
                namespace=self.ns_name,
                name=self.service_name,
                env=[
                    EnvVarArgs(
                        name="BLOCKY_CONFIG_FILE",
                        value=str(self.config_directory / self.config_file_name),
                    ),
                ],
                image=self.image,
                ports=[
                    ContainerPortArgs(
                        container_port=self.container_dns_port,
                        host_port=self.host_dns_port,
                        protocol="UDP",
                    ),
                ],
                privilege_drop_mode="pod-exec",
                volumes=[],
                config_map_volumes=[
                    HomelabContainerConfigMapVolumeArgs(
                        name="config",
                        mount_path=str(self.config_directory),
                        config_map=ConfigMapVolumeSourceArgs(
                            name=config_map.metadata["name"],
                            default_mode=0o444,
                        ),
                    ),
                ],
            ),
            dctx=self.dctx,
            opts=self.default_ropts,
        )

    def _config(self) -> dict[str, Any]:
        """
        Returns the Blocky configuration.
        """
        return {
            "upstreams": {
                "groups": {
                    "default": self.upstream_dns_servers,
                },
            },
            "blocking": {
                "denylists": {
                    "ads": self.ad_denylists,
                },
                "clientGroupsBlock": {
                    "default": ["ads"],
                },
            },
            "ports": {
                "dns": self.container_dns_port,
            },
            "specialUseDomains": {
                "enable": False,
            },
        }
