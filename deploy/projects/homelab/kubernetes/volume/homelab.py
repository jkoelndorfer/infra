"""
projects.homelab.kubernetes.volume.homelab
==========================================

This module contains homelab type definitions used in the creation of
Kubernetes persistent volumes.
"""

from dataclasses import dataclass
from typing import Any, get_args, Literal, Self, Sequence

import kubernetes

from infralib import DeploymentContext
from infralib.error import KubernetesNodeLookupError

from .types import AccessMode

HomelabBackingVolumeID = Literal["data0"]


@dataclass
class HomelabBackingVolume:
    """
    Physical storage that backs a Kubernetes persistent volume.
    """

    backing_volume: HomelabBackingVolumeID
    node_name: str
    node_ip: str
    volume_path: str

    @classmethod
    def lookup(
        cls,
        dctx: DeploymentContext,
        backing_volume_id: HomelabBackingVolumeID,
    ) -> Self:
        k8s_corev1 = dctx.provider_factory.kubernetes_client().CoreV1Api()
        volume_label = f"has.{backing_volume_id}.volume=true"
        matching_nodes = k8s_corev1.list_node(label_selector=volume_label).items  # pyright: ignore

        assert isinstance(matching_nodes, list)

        cnt = len(matching_nodes)
        if cnt != 1:
            raise KubernetesNodeLookupError(
                f"expected one node with backing volume {backing_volume_id}; got {cnt}"
            )
        n = matching_nodes[0]
        annotations = n.metadata.annotations

        addresses = n.status.addresses
        assert isinstance(addresses, list)
        node_ip = next(filter(lambda a: a.type == "InternalIP", addresses)).address

        return cls(
            backing_volume=backing_volume_id,
            node_name=n.metadata.name,
            node_ip=node_ip,
            volume_path=annotations[f"path.{backing_volume_id}.volume"],
        )

    def __repr__(self) -> str:
        return (
            self.__class__.__name__
            + f"({self.backing_volume}, "
            + f"node_name={self.node_name}, "
            + f"node_ip={self.node_ip}, "
            + f"volume_path={self.volume_path})"
        )


@dataclass
class HomelabPersistentVolume:
    """
    Class representing a Kubernetes persistent volume conforming to homelab
    standards.
    """

    basename: str
    """
    The base name of the volume. Homelab-provisioned persistent volume names
    take the form "${NAMESPACE}-${BASENAME}".
    """

    namespace: str
    """
    The namespace that owns the persistent volume.
    """

    access_modes: Sequence[AccessMode]
    """
    The permitted access modes for the persistent volume.
    """

    backing_volume: HomelabBackingVolumeID
    """
    The name of the physical storage device that backs the persistent volume.

    A backing volume is likely bound to a single node.
    """

    path: str
    """
    The path to this volume's data on the node that the backing volume is
    mounted on.
    """

    storage: str
    """
    The value of the persistent volume's capacity.storage value.
    """

    storage_class_name: str
    """
    The storage class name of the volume.
    """

    volume_reclaim_policy: str
    """
    The persistent volume's reclaim policy.
    """

    user: int
    """
    The UID of the volume's directory.
    """

    group: int
    """
    The GID of the volume's directory.
    """

    mode: str
    """
    The Unix file mode (octal permission set) of the volume's directory.
    """

    @property
    def name(self) -> str:
        """
        The full name of the volume. This includes the namespace prefix.
        """
        return self.name_for(self.namespace, self.basename)

    @classmethod
    def name_for(cls, namespace: str, basename: str) -> str:
        """
        Returns the full name for a standard HomelabPersistentVolume given a
        namespace and basename.
        """
        return f"{namespace}-{basename}"

    @classmethod
    def lookup(cls, dctx: DeploymentContext, name: str) -> Self:
        """
        Looks up a HomelabPersistentVolume with the given name.
        """
        kv1 = dctx.provider_factory.kubernetes_client().CoreV1Api()
        pv = kv1.read_persistent_volume(name)
        assert isinstance(pv, kubernetes.client.V1PersistentVolume)

        bv_base_untyped = pv.metadata.annotations["backing-volume"]  # pyright: ignore
        bv_base: HomelabBackingVolumeID = bv_base_untyped
        assert bv_base in get_args(HomelabBackingVolumeID)

        namespace = pv.metadata.annotations["namespace"]  # pyright: ignore
        user = pv.metadata.annotations["user"]  # pyright: ignore
        group = pv.metadata.annotations["group"]  # pyright: ignore
        mode = pv.metadata.annotations["mode"]  # pyright: ignore
        access_modes = pv.spec.access_modes  # pyright: ignore
        pv_path = pv.spec.local.path  # pyright: ignore
        storage = pv.spec.capacity["storage"]  # pyright: ignore
        storage_class_name = pv.spec.storage_class_name  # pyright: ignore
        volume_reclaim_policy = pv.spec.persistent_volume_reclaim_policy  # pyright: ignore

        basename = name.removeprefix(f"{namespace}-")

        return cls(
            basename=basename,
            namespace=namespace,
            access_modes=access_modes,
            backing_volume=bv_base,
            path=pv_path,
            storage=storage,
            storage_class_name=storage_class_name,
            volume_reclaim_policy=volume_reclaim_policy,
            user=user,
            group=group,
            mode=mode,
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(**d)


@dataclass
class HomelabPersistentVolumeClaim:
    name: str
    namespace: str
    access_modes: Sequence[AccessMode]
    backing_volume: HomelabBackingVolumeID

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(**d)
