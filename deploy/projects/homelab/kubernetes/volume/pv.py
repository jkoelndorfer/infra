"""
projects.homelab.kubernetes.volume.pv
=====================================

This module contains datastructures and provisioning logic for Kubernetes
persistent volumes.
"""

from dataclasses import dataclass
from typing import Sequence

from pulumi import (
    Input,
    Output,
    ResourceOptions,
)
import pulumi_command as command
import pulumi_kubernetes as k8s

from infralib import InfrastructureComponent

from .homelab import (
    HomelabBackingVolume,
    HomelabBackingVolumeID,
    HomelabPersistentVolume,
    HomelabPersistentVolumeClaim,
)
from .types import (
    AccessMode,
    VolumeReclaimPolicy,
)


@dataclass
class HomelabBackingVolumeAllocationArgs:
    """
    Arguments passed as part of HomelabKubernetesPersistentVolumeArgs that
    indicate that a new persistent volume should be allocated on the given
    backing volume with particular parameters.
    """

    # The Kubernetes API must be consulted to find nodes with the given
    # backing volume. This lookup happens outside any Pulumi provider, and
    # we need to raise an error if the lookup fails or returns unexpected
    # results. A HomelabBackingVolumeID must therefore be a plain string.
    backing_volume_id: HomelabBackingVolumeID
    """
    The ID of the backing volume that will store the data for the provisioned
    persistent volume.
    """

    storage: Input[str]
    """
    The value of the persistent volume's capacity.storage.
    """

    user: Input[int]
    """
    The UID of directory created for this persistent volume.
    """

    group: Input[int]
    """
    The GID of directory created for this persistent volume.
    """

    mode: Input[str]
    """
    The Unix file mode of the directory created for this persistent volume,
    represented in octal.
    """

    volume_reclaim_policy: Input[VolumeReclaimPolicy] = "Retain"
    """
    The reclaim policy for this volume. Defaults to "Retain".
    """


@dataclass
class HomelabKubernetesPersistentVolumeArgs:
    """
    Arguments passed to a KubernetesPersistentVolume.
    """

    namespace: Input[str]
    """
    The namespace that owns the created persistent volume.
    """

    basename: Input[str]
    """
    The basename of the persistent volume to be created.
    """

    backing_volume: HomelabBackingVolumeAllocationArgs | HomelabPersistentVolume
    """
    The volume whose storage physically backs this persistent volume.

    A HomelabPersistentVolume acts as a pointer to an already-existing
    persistent volume. The newly-provisioned persistent volume will be
    backed by the same directory, on the same homelab backing volume.
    """

    access_modes: Input[Sequence[Input[AccessMode]]]
    """
    A list of permitted persistent volume access modes for this volume.
    """

    import_name: str | None = None
    """
    The name of a persistent volume to import. Importing will only be attempted
    if import_name is specified.
    """


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

    @classmethod
    def pv_full_name(
        cls,
        namespace: str,
        basename: str,
    ) -> str:
        """
        Given an associated namespace and a volume name, returns the full name of
        the PersistentVolume.
        """
        return f"{namespace}-{basename}"

    @classmethod
    def pv_full_name_input(
        cls,
        namespace: Input[str],
        basename: Input[str],
    ) -> Output[str]:
        """
        Given an associated namespace and a volume name, returns the full name of
        the PersistentVolume. This function accepts Pulumi Inputs and returns a
        Pulumi Output.
        """
        return Output.all(
            namespace=namespace,
            basename=basename,
        ).apply(lambda d: cls.pv_full_name(d["namespace"], d["basename"]))

    def provision(self) -> None:
        self._pvsetup_cmd: command.local.Command | None = None

        self._volume_ropts = self.default_ropts
        if self.args.import_name is not None:
            self._volume_ropts = self.default_ropts.merge(
                ResourceOptions(import_=self.args.import_name)
            )

        if isinstance(self.args.backing_volume, HomelabPersistentVolume):
            self._bv = HomelabBackingVolume.lookup(
                self.dctx, self.args.backing_volume.backing_volume
            )
            self._pv_path: Input[str] = self.args.backing_volume.path

            # If another PersistentVolume is our data store, we don't need to
            # perform directory setup.
            do_pvsetup = False
        else:
            self._bv = HomelabBackingVolume.lookup(
                self.dctx, self.args.backing_volume.backing_volume_id
            )
            _volume_subpath = Output.all(
                namespace=self.args.namespace,
                basename=self.args.basename,
            ).apply(lambda d: f"{d['namespace']}/{d['basename']}")
            self._pv_path = _volume_subpath.apply(
                lambda p: f"{self._bv.volume_path}/{p}"
            )
            do_pvsetup = True

        self._name_output = self.pv_full_name_input(
            namespace=self.args.namespace,
            basename=self.args.basename,
        )

        if do_pvsetup:
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
                "PV_DIRECTORY": self._pv_path,
                "PV_USER": Output.from_input(self.args.backing_volume.user).apply(
                    lambda x: str(x)
                ),
                "PV_GROUP": Output.from_input(self.args.backing_volume.group).apply(
                    lambda x: str(x)
                ),
                "PV_MODE": self.args.backing_volume.mode,
                "REMOTE_HOST": self._bv.node_ip,
            },
            opts=cmd_ropts,
        )

    def _provision_pv(self) -> None:
        """
        Provisions the Kubernetes PersistentVolume resource.
        """
        pv_ropts = self._volume_ropts
        if self._pvsetup_cmd is not None:
            pv_ropts = pv_ropts.merge(ResourceOptions(depends_on=[self._pvsetup_cmd]))

        if isinstance(self.args.backing_volume, HomelabPersistentVolume):
            # The volume to be provisioned references the data directory of
            # another volume. Deletion of the new volume should not trigger
            # destruction of the data for the original volume.
            volume_reclaim_policy: Input[VolumeReclaimPolicy] = "Retain"
        else:
            volume_reclaim_policy = self.args.backing_volume.volume_reclaim_policy

        self._pv_r = k8s.core.v1.PersistentVolume(
            resource_name=f"{self.name}_pv",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                annotations={
                    "backing-volume": self._bv.backing_volume,
                    "namespace": self.args.namespace,
                    "mode": self.args.backing_volume.mode,
                    "user": Output.from_input(self.args.backing_volume.user).apply(
                        lambda u: str(u)
                    ),
                    "group": Output.from_input(self.args.backing_volume.group).apply(
                        lambda g: str(g)
                    ),
                },
                name=self._name_output,
                namespace=self.args.namespace,
            ),
            spec=k8s.core.v1.PersistentVolumeSpecArgs(
                access_modes=self.args.access_modes,
                capacity={
                    "storage": self.args.backing_volume.storage,
                },
                local=k8s.core.v1.LocalVolumeSourceArgs(path=self._pv_path),
                persistent_volume_reclaim_policy=volume_reclaim_policy,
                storage_class_name=self.STORAGE_CLASS,
                node_affinity=k8s.core.v1.VolumeNodeAffinityArgs(
                    required=k8s.core.v1.NodeSelectorArgs(
                        node_selector_terms=[
                            k8s.core.v1.NodeSelectorTermArgs(
                                match_expressions=[
                                    k8s.core.v1.NodeSelectorRequirementArgs(
                                        key=f"has.{self._bv.backing_volume}.volume",
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
            opts=pv_ropts,
        )
        pv_dict = {
            "basename": self.args.basename,
            "namespace": self.args.namespace,
            "access_modes": self._pv_r.spec.access_modes,
            "backing_volume": self._bv.backing_volume,
            "path": self._pv_r.spec.local.path,
            "storage": self._pv_r.spec.capacity["storage"],
            "storage_class_name": self._pv_r.spec.storage_class_name,
            "volume_reclaim_policy": self._pv_r.spec.persistent_volume_reclaim_policy,
            "user": self._pv_r.metadata.annotations["user"],
            "group": self._pv_r.metadata.annotations["group"],
            "mode": self._pv_r.metadata.annotations["mode"],
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
                name=self.args.basename,
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
            "backing_volume": self._bv.backing_volume,
        }
        self.output(
            name="pvc",
            v=pvc_dict,
        )
        self.pvc = Output.from_input(pvc_dict).apply(
            lambda d: HomelabPersistentVolumeClaim.from_dict(d)
        )
