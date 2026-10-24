"""
projects.homelab.kubernetes.refvolume
=====================================

This module contains components to provision a Kubernetes reference persistent
volume and persistent volume claim.

A "reference persistent volume" points at the underlying directory of another
persistent volume. This is used to expose the data of a service to a service
in a different namespace.
"""

from dataclasses import dataclass
from typing import Sequence

from pulumi import Input, Output

from infralib import InfrastructureComponent

from .volume import (
    AccessMode,
    HomelabKubernetesPersistentVolume,
    HomelabKubernetesPersistentVolumeArgs,
    HomelabPersistentVolume,
    HomelabPersistentVolumeClaim,
)


@dataclass
class HomelabKubernetesReferencePersistentVolumeArgs:
    """
    Arguments passed to a KubernetesPersistentVolume.
    """

    namespace: Input[str]
    """
    The namespace that this reference persistent volume is created in.
    """

    ref_name: str
    """
    The full name of the persistent volume being referred to.
    """

    access_modes: Input[Sequence[Input[AccessMode]]]
    """
    Access modes that are permitted for the reference persistent volume.
    """


class HomelabKubernetesReferencePersistentVolume(
    InfrastructureComponent[HomelabKubernetesReferencePersistentVolumeArgs]
):
    """
    A persistent volume that points at the underlying directory of another
    persistent volume.
    """

    pv: Output[HomelabPersistentVolume]
    pvc: Output[HomelabPersistentVolumeClaim]

    def provision(self) -> None:
        args = self._ref_args()
        vol = HomelabKubernetesPersistentVolume(
            f"{self.name}_pv",
            args,
            self.dctx,
            opts=self.default_ropts,
        )
        self.pv = vol.pv
        self.pvc = vol.pvc

    def _ref_pv_name(self, pv_name: Input[str]) -> Output[str]:
        """
        Returns the name of the reference persistent volume.
        """
        return Output.from_input(pv_name).apply(lambda n: f"ref-{n}")

    def _ref_args(self) -> HomelabKubernetesPersistentVolumeArgs:
        """
        Looks up the referenced volume and returns a set of
        HomelabKubernetesPersistentVolumeArgs that are appropriate to provision
        a reference volume.
        """
        homelab_pv = HomelabPersistentVolume.lookup(self.dctx, self.args.ref_name)

        return HomelabKubernetesPersistentVolumeArgs(
            basename=self._ref_pv_name(self.args.ref_name),
            namespace=self.args.namespace,
            backing_volume=homelab_pv,
            access_modes=self.args.access_modes,
        )
