"""
projects.homelab.kubernetes.deployment
======================================

This module contains the definition for a standard Kubernetes
service deployment.
"""

from dataclasses import dataclass, field
import json
from typing import Literal, Sequence

from pulumi import Input, Output
import pulumi_kubernetes as k8s

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureComponent,
)
from ..traefik import (
    default_route_transformer,
    TraefikIngressRoute,
    TraefikIngressRouteArgs,
    TraefikIngressRouteTLSDomain,
    TraefikRouteBuilder,
    TraefikRouteTransformer,
)
from .service import HomelabService
from .uid_gid import uid_gid
from .volume import (
    AccessMode,
    HomelabBackingVolume,
    HomelabKubernetesPersistentVolume,
    HomelabKubernetesPersistentVolumeArgs,
    HomelabPersistentVolume,
    HomelabPersistentVolumeClaim,
    VolumeReclaimPolicy,
)


@dataclass
class HomelabContainerVolumeProvisionedSource:
    """
    Class that describes a persistent volume to provision for the deployment.
    """

    backing_volume: HomelabBackingVolume
    storage: Input[str]
    access_modes: Input[Sequence[Input[AccessMode]]]
    mode: Input[str]
    volume_reclaim_policy: Input[VolumeReclaimPolicy] = "Retain"


@dataclass
class HomelabContainerVolumeArgs:
    """
    Class that defines a homelab Kubernetes deployment volume.
    """

    name: str
    mount_path: str
    source: HomelabContainerVolumeProvisionedSource
    read_only: bool


@dataclass
class HomelabHTTPSDeploymentIngressArgs:
    """
    Class that provides arguments to a deployment for establishing a standard
    HTTPS ingress and associated service.
    """

    container_port: int
    hostname: str | None = None
    san_hostnames: list[str] = field(default_factory=list)
    traefik_route_transform: TraefikRouteTransformer = default_route_transformer


@dataclass
class HomelabProvisionedContainerVolume:
    """
    Class that describes a homelab Kubernetes deployment volume
    that has been provisioned.
    """

    name: str
    mount_path: str
    persistent_volume: Output[HomelabPersistentVolume]
    persistent_volume_claim: Output[HomelabPersistentVolumeClaim]
    volume_args: k8s.core.v1.VolumeArgs
    volume_mount_args: k8s.core.v1.VolumeMountArgs


@dataclass
class HomelabKubernetesDeploymentArgs:
    """
    Class that provides arguments to a standard homelab Kubernetes deployment.
    """

    namespace: Input[str]
    name: str

    https_ingress: HomelabHTTPSDeploymentIngressArgs
    image: str
    volumes: list[HomelabContainerVolumeArgs]
    command: Input[Sequence[Input[str]]] | None = None
    env: list[k8s.core.v1.EnvVarArgs] = field(default_factory=list)
    ports: list[k8s.core.v1.ContainerPortArgs] = field(default_factory=list)
    image_pull_policy: Literal["Always", "IfNotPresent", "Never"] = "IfNotPresent"
    privilege_drop_mode: Literal["pod-exec", "s6-entrypoint", None] = "pod-exec"


class HomelabKubernetesDeployment(
    InfrastructureComponent[HomelabKubernetesDeploymentArgs]
):
    """
    Component that provisions a Kubernetes deployment in accordance with homelab standards.
    """

    def provision(self) -> None:
        self.service_label = {
            "service-name": self.args.name,
        }
        self.label_selector = k8s.meta.v1.LabelSelectorArgs(
            match_labels=self.service_label
        )
        self.service_user_group = uid_gid(self.dctx.target.environment, self.args.name)
        self.output("service_label", self.service_label)

        volumes = self._provision_volumes()
        self._provision_deployment(volumes)
        self._provision_https_ingress_service()

    def _provision_deployment(self, volumes: list[HomelabProvisionedContainerVolume]):
        """
        Provisions the deployment.
        """
        if self.args.privilege_drop_mode == "s6-entrypoint":
            addl_env = [
                k8s.core.v1.EnvVarArgs(
                    name="PUID",
                    value=str(self.service_user_group),
                ),
                k8s.core.v1.EnvVarArgs(
                    name="PGID",
                    value=str(self.service_user_group),
                ),
            ]
        else:
            addl_env = []

        container_args = k8s.core.v1.ContainerArgs(
            name=self.args.name,
            command=self.args.command,
            image=self.args.image,
            image_pull_policy=self.args.image_pull_policy,
            env=[*self.args.env, *addl_env],
            ports=self.args.ports,
            volume_mounts=[v.volume_mount_args for v in volumes],
        )

        # TODO: Image pull secrets
        if self.args.privilege_drop_mode == "pod-exec":
            pod_security_context = k8s.core.v1.PodSecurityContextArgs(
                run_as_user=self.service_user_group,
                run_as_group=self.service_user_group,
                run_as_non_root=True,
            )
        else:
            pod_security_context = None

        pod_spec = k8s.core.v1.PodSpecArgs(
            containers=[container_args],
            security_context=pod_security_context,
            volumes=[v.volume_args for v in volumes],
        )

        deployment_spec = k8s.apps.v1.DeploymentSpecArgs(
            selector=self.label_selector,
            strategy=k8s.apps.v1.DeploymentStrategyArgs(
                type="Recreate",
            ),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    namespace=self.args.namespace,
                    name=self.args.name,
                    labels=self.service_label,
                ),
                spec=pod_spec,
            ),
        )

        self.deployment = k8s.apps.v1.Deployment(
            "deployment",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.args.namespace,
                name=self.args.name,
            ),
            spec=deployment_spec,
            opts=self.default_ropts,
        )
        self.output(
            "deployment",
            {
                "namespace": self.deployment.metadata["namespace"],
                "name": self.deployment.metadata["name"],
            },
        )

    def _provision_https_ingress_service(self) -> None:
        """
        Provisions the default HTTPS ingress and service, if required.
        """
        if self.args.https_ingress is None:
            return

        homelab_domain = self.dctx.config.domains["homelab"].domain_for(
            self.dctx.target
        )
        hostname = self.args.https_ingress.hostname or self.args.name
        service_name = f"{self.args.name}-http"

        k8s.core.v1.Service(
            f"{self.name}_service",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.args.namespace,
                name=service_name,
            ),
            spec=k8s.core.v1.ServiceSpecArgs(
                type=k8s.core.v1.ServiceSpecType.CLUSTER_IP,
                selector=self.service_label,
                ports=[
                    k8s.core.v1.ServicePortArgs(
                        port=self.args.https_ingress.container_port,
                        name="http",
                    ),
                ],
            ),
            opts=self.default_ropts,
        )

        homelab_service = HomelabService(
            service_name,
            self.args.https_ingress.container_port,
            hostname,
            homelab_domain,
        )
        route_builder = TraefikRouteBuilder(homelab_service)
        self.ingress_route = TraefikIngressRoute(
            self.name,
            TraefikIngressRouteArgs(
                namespace=self.args.namespace,
                name=f"{self.args.name}-https-ingress",
                routes=self.args.https_ingress.traefik_route_transform(
                    route_builder, [route_builder.route()]
                ),
                tls_domains=[
                    TraefikIngressRouteTLSDomain(
                        main=hostname,
                        sans=self.args.https_ingress.san_hostnames,
                    ),
                ],
            ),
            self.dctx,
            opts=self.default_ropts,
        )

    def _provision_volumes(self) -> list[HomelabProvisionedContainerVolume]:
        """
        Provisions volumes used by the deployment and returns VolumeArgs that
        can be used to mount them.
        """
        vols: list[HomelabProvisionedContainerVolume] = list()
        for v in self.args.volumes:
            volume_args = HomelabKubernetesPersistentVolumeArgs(
                name=v.name,
                namespace=self.args.namespace,
                backing_volume=v.source.backing_volume,
                storage=v.source.storage,
                access_modes=v.source.access_modes,
                user=self.service_user_group,
                group=self.service_user_group,
                mode=v.source.mode,
                volume_reclaim_policy=v.source.volume_reclaim_policy,
            )
            allocated_volume = HomelabKubernetesPersistentVolume(
                f"{self.name}_{v.name}",
                volume_args,
                self.dctx,
                self.default_ropts,
            )
            vols.append(
                HomelabProvisionedContainerVolume(
                    name=v.name,
                    mount_path=v.mount_path,
                    persistent_volume=allocated_volume.pv,
                    persistent_volume_claim=allocated_volume.pvc,
                    volume_args=k8s.core.v1.VolumeArgs(
                        name=v.name,
                        persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                            claim_name=allocated_volume.pvc.name,
                            read_only=v.read_only,
                        ),
                    ),
                    volume_mount_args=k8s.core.v1.VolumeMountArgs(
                        name=v.name,
                        mount_path=v.mount_path,
                        read_only=v.read_only,
                    ),
                )
            )

        return vols

    def _image_pull_secrets(self) -> list[k8s.core.v1.LocalObjectReferenceArgs]:
        """
        Returns appropriate image pull secrets for the container, if any are required.
        """
        homelab_domain = self.dctx.config.domains["homelab"].domain_for(
            DeploymentTarget(Environment.PROD, None)
        )
        image_pull_secrets: list[k8s.core.v1.LocalObjectReferenceArgs] = list()

        if f".{homelab_domain}/" in self.args.image:
            # Any container images pulled from our homelab domain are local.
            #
            # We need to pass container registry credentials.
            homelab_image_secret = k8s.core.v1.Secret(
                f"{self.name}_homelab_image_pull",
                metadata=k8s.meta.v1.ObjectMetaArgs(
                    namespace=self.args.namespace,
                    name="homelab-image-pull",
                ),
                type="kubernetes.io/dockerconfigjson",
                string_data={
                    ".dockerconfigjson": Output.all(
                        ctr_registry_ro_hostname="TODO",
                        username="TODO",
                        password="TODO",
                    ).apply(
                        lambda d: json.dumps(
                            {
                                "auths": {
                                    f"{d['ctr_registry_ro_hostname']}/": {
                                        "username": d["username"],
                                        "password": d["password"],
                                    },
                                },
                            }
                        )
                    ),
                },
                opts=self.default_ropts,
            )
            image_pull_secrets.append(
                k8s.core.v1.LocalObjectReferenceArgs(
                    name=homelab_image_secret.metadata.name,
                )
            )

        return image_pull_secrets
