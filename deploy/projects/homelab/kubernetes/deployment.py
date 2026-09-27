"""
projects.homelab.kubernetes.deployment
======================================

This module contains the definition for a standard Kubernetes
service deployment.
"""

from dataclasses import dataclass, field
import json
from typing import Any, Callable, Literal, Sequence

from pulumi import Input, Output
import pulumi_kubernetes as k8s

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureComponent,
)
from ..traefik import HomelabTraefikProject
from .volume import (
    HomelabKubernetesPersistentVolume,
    HomelabKubernetesPersistentVolumeArgs,
    HomelabPersistentVolume,
    HomelabPersistentVolumeClaim,
)


TraefikRoute = dict[str, Any]


@dataclass
class TraefikRouteTranformInput:
    """
    Data provided to a Traefik route transformation function.
    """

    default_route: TraefikRoute
    """
    The default route that is configured to serve traffic.
    """

    container_port: int
    """
    The port that the container receives HTTP traffic on.
    """

    hostname: str
    """
    The service's default hostname. This is the first part of the fully-qualified
    domain name. It excludes the domain.
    """

    domain: str
    """
    The second part of the fully-qualified domain name. It excludes the hostname.
    """

    fqdn: str
    """
    The fully-qualified domain name of the service. Effectively: f"{hostname}.{domain}".

    This is the value matched against the Host in the default route.
    """


TraefikRouteTransformer = Callable[[TraefikRouteTranformInput], list[TraefikRoute]]


@dataclass
class HomelabContainerVolumeArgs:
    """
    Class that defines a homelab Kubernetes deployment volume.
    """

    name: str
    mount_path: str
    source: HomelabKubernetesPersistentVolumeArgs
    read_only: bool


@dataclass
class HomelabHTTPSIngressServiceArgs:
    """
    Class that provides arguments to a deployment for establishing a standard
    HTTPS ingress and associated service.
    """

    container_port: int
    hostname: str | None = None
    san_hostnames: list[str] = field(default_factory=list)
    route_transform: TraefikRouteTransformer = lambda i: [i.default_route]


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

    namespace: str
    name: str

    https_ingress: HomelabHTTPSIngressServiceArgs
    image: str
    image_pull_policy: Input[str]
    volumes: list[HomelabContainerVolumeArgs]
    command: Input[Sequence[Input[str]]] | None = None
    env: list[k8s.core.v1.EnvVarArgs] = field(default_factory=list)
    ports: list[k8s.core.v1.ContainerPortArgs] = field(default_factory=list)
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
        self.output("service_label", self.service_label)

        volumes = self._provision_volumes()
        self._provision_deployment(volumes)

    def _provision_deployment(self, volumes: list[HomelabProvisionedContainerVolume]):
        """
        Provisions the deployment.
        """
        container_args = k8s.core.v1.ContainerArgs(
            name=self.args.name,
            command=self.args.command,
            image=self.args.image,
            image_pull_policy=self.args.image_pull_policy,
            env=self.args.env,
            ports=self.args.ports,
            volume_mounts=[v.volume_mount_args for v in volumes],
        )

        pod_spec = k8s.core.v1.PodSpecArgs(
            containers=[container_args],
            image_pull_secrets=self._image_pull_secrets(),
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
        fqdn = f"{hostname}.{homelab_domain}"

        k8s.core.v1.Service(
            f"{self.name}_service",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.args.namespace,
                name=Output.from_input(self.args.name).apply(lambda n: f"{n}-http"),
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

        default_route = {
            "match": f"Host(`{fqdn}`)",
            "port": self.args.https_ingress.container_port,
            "kind": "Service",
        }
        route_transform_input = TraefikRouteTranformInput(
            default_route,
            self.args.https_ingress.container_port,
            hostname,
            homelab_domain,
            fqdn,
        )
        k8s.apiextensions.CustomResource(
            f"{self.name}_traefik_ingress",
            api_version="traefik.io/v1alpha1",
            kind="IngressRoute",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.args.namespace,
                name=Output.from_input(self.args.name).apply(
                    lambda n: f"{n}-https-route"
                ),
            ),
            spec={
                "routes": self.args.https_ingress.route_transform(
                    route_transform_input
                ),
                "tls": {
                    "certResolver": HomelabTraefikProject.cert_resolver,
                    "domains": [
                        {
                            "main": fqdn,
                            "sans": [
                                f"{h}.{homelab_domain}"
                                for h in self.args.https_ingress.san_hostnames
                            ],
                        },
                    ],
                },
            },
            opts=self.default_ropts,
        )

    def _provision_volumes(self) -> list[HomelabProvisionedContainerVolume]:
        """
        Provisions volumes used by the deployment and returns VolumeArgs that
        can be used to mount them.
        """
        vols: list[HomelabProvisionedContainerVolume] = list()
        for v in self.args.volumes:
            allocated_volume = HomelabKubernetesPersistentVolume(
                f"{self.name}_{v.name}",
                v.source,
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
