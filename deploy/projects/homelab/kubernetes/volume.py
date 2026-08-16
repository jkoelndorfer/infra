"""
projects.homelab.kubernetes.volume
==================================

This module contains components to provision a Kubernetes persistent volume
and persistent volume claim.
"""

from dataclasses import dataclass
from typing import Any, Literal, Self, Sequence

from pulumi import (
    Input,
    Output,
    ResourceOptions,
)
import pulumi_command as command
import pulumi_kubernetes as k8s

from infralib import (
    DeploymentContext,
    InfrastructureComponent,
)
from infralib.error import KubernetesNodeLookupError

AccessMode = Literal[
    "ReadWriteOnce",
    "ReadOnlyMany",
    "ReadWriteMany",
    "ReadWriteOncePod",
]
HomelabBackingVolume = Literal["data0"]
VolumeReclaimPolicy = Literal["Retain", "Recycle", "Delete"]


@dataclass
class HomelabBackingVolumeDescription:
    """
    Describes a backing volume on a Kubernetes node.
    """

    backing_volume: HomelabBackingVolume
    node_name: str
    node_ip: str
    volume_path: str

    def __repr__(self) -> str:
        return (
            self.__class__.__name__
            + f"({self.backing_volume}, "
            + f"node_name={self.node_name}, "
            + f"node_ip={self.node_ip}, "
            + f"volume_path={self.volume_path})"
        )


def describe_backing_volume(
    dctx: DeploymentContext,
    volume: HomelabBackingVolume,
) -> HomelabBackingVolumeDescription:
    """
    Describes a Kubernetes backing volume.
    """
    k8s_corev1 = dctx.provider_factory.kubernetes_client().CoreV1Api()
    volume_label = f"has.{volume}.volume=true"
    matching_nodes = k8s_corev1.list_node(label_selector=volume_label).items  # pyright: ignore

    assert isinstance(matching_nodes, list)

    cnt = len(matching_nodes)
    if cnt != 1:
        raise KubernetesNodeLookupError(
            f"expected one node with backing volume {volume}; got {cnt}"
        )
    n = matching_nodes[0]
    annotations = n.metadata.annotations

    addresses = n.status.addresses
    assert isinstance(addresses, list)
    node_ip = next(filter(lambda a: a.type == "InternalIP", addresses)).address

    return HomelabBackingVolumeDescription(
        backing_volume=volume,
        node_name=n.metadata.name,
        node_ip=node_ip,
        volume_path=annotations[f"path.{volume}.volume"],
    )


@dataclass
class HomelabPersistentVolume:
    name: str
    namespace: str
    access_modes: Sequence[AccessMode]
    backing_volume: HomelabBackingVolume
    path: str
    storage: str
    storage_class_name: str
    volume_reclaim_policy: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(**d)


@dataclass
class HomelabPersistentVolumeClaim:
    name: str
    namespace: str
    access_modes: Sequence[AccessMode]
    backing_volume: HomelabBackingVolume

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(**d)


@dataclass
class HomelabKubernetesPersistentVolumeArgs:
    """
    Arguments passed to a KubernetesPersistentVolume.
    """

    name: Input[str]
    namespace: Input[str]

    # The Kubernetes API must be consulted to find nodes with the given
    # backing_volume. This lookup happens outside any Pulumi provider, and
    # we need to raise an error if the lookup fails or returns unexpected
    # results.
    #
    # For that reason, backing_volume must be a plain string, not an Input.
    backing_volume: HomelabBackingVolume

    storage: Input[str]
    access_modes: Input[Sequence[Input[AccessMode]]]
    user: Input[int]
    group: Input[int]
    mode: Input[str]
    volume_reclaim_policy: Input[VolumeReclaimPolicy] = "Retain"

    import_name: str | None = None


class HomelabKubernetesPersistentVolume(
    InfrastructureComponent[HomelabKubernetesPersistentVolumeArgs]
):
    # This is the storage class that ships with k3s to
    # configure local directories.
    #
    # See https://docs.k3s.io/storage
    STORAGE_CLASS = "local-path"

    pv: Output[HomelabPersistentVolume]
    pvc: Output[HomelabPersistentVolumeClaim]

    def provision(self) -> None:
        self._bv = describe_backing_volume(self.dctx, self.args.backing_volume)

        if self.args.import_name is not None:
            self._volume_ropts = self.default_ropts.merge(
                ResourceOptions(import_=self.args.import_name)
            )
        else:
            self._volume_ropts = self.default_ropts

        self._name_output = Output.all(
            namespace=self.args.namespace,
            name=self.args.name,
        ).apply(lambda d: f"{d['namespace']}-{d['name']}")

        self._volume_subpath = Output.all(
            namespace=self.args.namespace,
            name=self.args.name,
        ).apply(lambda d: f"{d['namespace']}/{d['name']}")
        self._volume_path = self._volume_subpath.apply(
            lambda p: f"{self._bv.volume_path}/{p}"
        )

        self._provision_local_path()
        self._provision_pv()
        self._provision_pvc()

    def _provision_local_path(self) -> None:
        """
        Provisions a directory on the host filesystem that stores the
        PersistentVolume's data.
        """
        command_provider = self.dctx.provider_factory.command_provider()
        cmd_ropts = self.default_ropts.merge(ResourceOptions(provider=command_provider))

        self._pvsetup_cmd = command.local.Command(
            f"{self.name}_pvsetup",
            create="${INFRALIB_DEPLOY_ROOT}/projects/homelab/kubernetes/pvsetup",
            environment={
                "PV_DIRECTORY": self._volume_path,
                "PV_USER": Output.from_input(self.args.user).apply(lambda x: str(x)),
                "PV_GROUP": Output.from_input(self.args.group).apply(lambda x: str(x)),
                "PV_MODE": self.args.mode,
                "REMOTE_HOST": self._bv.node_ip,
            },
            opts=cmd_ropts,
        )

    def _provision_pv(self) -> None:
        """
        Provisions the Kubernetes PersistentVolume resource.
        """
        self._pv_r = k8s.core.v1.PersistentVolume(
            resource_name=f"{self.name}_pv",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name=self._name_output,
                namespace=self.args.namespace,
            ),
            spec=k8s.core.v1.PersistentVolumeSpecArgs(
                access_modes=self.args.access_modes,
                capacity={
                    "storage": self.args.storage,
                },
                local=k8s.core.v1.LocalVolumeSourceArgs(path=self._volume_path),
                persistent_volume_reclaim_policy=self.args.volume_reclaim_policy,
                storage_class_name=self.STORAGE_CLASS,
                node_affinity=k8s.core.v1.VolumeNodeAffinityArgs(
                    required=k8s.core.v1.NodeSelectorArgs(
                        node_selector_terms=[
                            k8s.core.v1.NodeSelectorTermArgs(
                                match_expressions=[
                                    k8s.core.v1.NodeSelectorRequirementArgs(
                                        key=f"has.{self.args.backing_volume}.volume",
                                        operator="In",
                                        values=["true"],
                                    )
                                ]
                            )
                        ]
                    ),
                ),
                volume_mode="Filesystem",
            ),
            opts=self._volume_ropts.merge(
                ResourceOptions(depends_on=[self._pvsetup_cmd])
            ),
        )
        pv_dict = {
            "name": self._pv_r.metadata.name,
            "namespace": self._pv_r.metadata.namespace,
            "access_modes": self._pv_r.spec.access_modes,
            "backing_volume": self.args.backing_volume,
            "path": self._pv_r.spec.local.path,
            "storage": self._pv_r.spec.capacity["storage"],
            "storage_class_name": self._pv_r.spec.storage_class_name,
            "volume_reclaim_policy": self._pv_r.spec.persistent_volume_reclaim_policy,
        }
        self.output(name="pv", v=pv_dict)
        self.pv = Output.from_input(pv_dict).apply(
            lambda d: HomelabPersistentVolume(**d)  # type: ignore
        )

    def _provision_pvc(self) -> None:
        """
        Provisions a Kubernetes PersistentVolumeClaim for the created PersistentVolume.
        """
        self._pvc_r = k8s.core.v1.PersistentVolumeClaim(
            resource_name=f"{self.name}_pvc",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name=self.args.name,
                namespace=self.args.namespace,
            ),
            spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
                access_modes=self.args.access_modes,
                volume_name=self._pv_r.metadata.name,
                resources=k8s.core.v1.VolumeResourceRequirementsArgs(
                    requests={
                        "storage": self._pv_r.spec.capacity["storage"],
                    },
                ),
            ),
            opts=self._volume_ropts,
        )
        pvc_dict = {
            "name": self._pvc_r.metadata.name,
            "namespace": self._pvc_r.metadata.namespace,
            "access_modes": self._pvc_r.spec.access_modes,
            "backing_volume": self.args.backing_volume,
        }
        self.output(
            name="pvc",
            v=pvc_dict,
        )
        self.pvc = HomelabPersistentVolumeClaim(**pvc_dict)  # type: ignore
