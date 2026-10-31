"""
projects.homelab.backup.volume
==============================

This module configures volumes for backups.
"""

from dataclasses import dataclass

from infralib import (
    DeploymentContext,
)

from pulumi import (
    Input,
    ResourceOptions,
)

from ..kubernetes import (
    AccessMode,
    HomelabBackingVolumeAllocationArgs,
    HomelabBackingVolumeID,
    HomelabKubernetesPersistentVolume,
    HomelabKubernetesPersistentVolumeArgs,
    HomelabKubernetesReferencePersistentVolume,
    HomelabKubernetesReferencePersistentVolumeArgs,
)
from ..syncthing import HomelabSyncthingProject
from ..vaultwarden import HomelabVaultwardenProject


@dataclass
class RefVolumeProvisionResult:
    """
    Result of provisioning backup reference persistent volumes.
    """

    vaultwarden_data: HomelabKubernetesReferencePersistentVolume
    syncthing_data: HomelabKubernetesReferencePersistentVolume
    syncthing_config: HomelabKubernetesReferencePersistentVolume


def provision_archive_volume(
    dctx: DeploymentContext,
    namespace: Input[str],
    backing_volume: HomelabBackingVolumeID,
    k8s_opts: ResourceOptions,
) -> HomelabKubernetesPersistentVolume:
    """
    Provisions the persistent volume that temporarily stores archival data.

    The archive data is backed up to a restic repository hosted on cloud
    storage on an ad-hoc basis.
    """
    return HomelabKubernetesPersistentVolume(
        "archive",
        HomelabKubernetesPersistentVolumeArgs(
            namespace=namespace,
            basename="archive",
            backing_volume=HomelabBackingVolumeAllocationArgs(
                backing_volume_id=backing_volume,
                storage="100Gi",
                user=0,
                group=0,
                mode="0755",
            ),
            access_modes=["ReadWriteOnce"],
        ),
        dctx,
        k8s_opts,
    )


def provision_local_backup_volume(
    dctx: DeploymentContext,
    namespace: Input[str],
    backing_volume: HomelabBackingVolumeID,
    k8s_opts: ResourceOptions,
) -> HomelabKubernetesPersistentVolume:
    """
    Provisions the persistent volume that stores the local restic repository.
    """
    return HomelabKubernetesPersistentVolume(
        "local_backup",
        HomelabKubernetesPersistentVolumeArgs(
            namespace=namespace,
            basename="local-backup",
            backing_volume=HomelabBackingVolumeAllocationArgs(
                backing_volume_id=backing_volume,
                storage="300Gi",
                user=0,
                group=0,
                mode="0755",
            ),
            access_modes=["ReadWriteOnce"],
        ),
        dctx,
        k8s_opts,
    )


def provision_ref_volumes(
    dctx: DeploymentContext,
    namespace: Input[str],
    k8s_opts: ResourceOptions,
) -> RefVolumeProvisionResult:
    """
    Provisions reference persistent volumes that enable backups to access
    the data of other services.
    """

    access_mode_ro: AccessMode = "ReadOnlyMany"

    def v(
        resource_name: str, name: str, access_mode: AccessMode
    ) -> HomelabKubernetesReferencePersistentVolume:
        return HomelabKubernetesReferencePersistentVolume(
            resource_name,
            HomelabKubernetesReferencePersistentVolumeArgs(
                namespace,
                name,
                [access_mode],
            ),
            dctx,
            k8s_opts,
        )

    vaultwarden_data = v(
        "vaultwarden_data",
        HomelabVaultwardenProject.data_pv(dctx, dctx.target).name,
        access_mode_ro,
    )

    syncthing_data = v(
        "syncthing_data",
        HomelabSyncthingProject.data_pv(dctx, dctx.target).name,
        access_mode_ro,
    )

    syncthing_config = v(
        "syncthing_config",
        HomelabSyncthingProject.config_pv(dctx, dctx.target).name,
        access_mode_ro,
    )

    return RefVolumeProvisionResult(
        vaultwarden_data,
        syncthing_data,
        syncthing_config,
    )
