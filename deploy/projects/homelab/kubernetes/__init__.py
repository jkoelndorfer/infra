"""
projects.homelab.kubernetes
===========================

This module contains helpers for homelab Kubernetes projects.
"""

from .deployment import (
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabHTTPSDeploymentIngressArgs,
    HomelabKubernetesDeploymentArgs,
    HomelabKubernetesDeployment,
)
from .imagepull import ImagePullCredential, ImagePullSecretProvider
from .refvolume import (
    HomelabKubernetesReferencePersistentVolume,
    HomelabKubernetesReferencePersistentVolumeArgs,
)
from .resources import helm_release, namespace
from .secret import decode_secret
from .service import HomelabService, service_domain, service_fqdn
from .uid_gid import uid_gid
from .volume import (
    AccessMode,
    HomelabBackingVolumeAllocationArgs,
    HomelabBackingVolumeID,
    HomelabKubernetesPersistentVolume,
    HomelabKubernetesPersistentVolumeArgs,
    HomelabPersistentVolume,
    HomelabPersistentVolumeClaim,
)

__all__ = [
    "AccessMode",
    "decode_secret",
    "helm_release",
    "HomelabBackingVolumeAllocationArgs",
    "HomelabBackingVolumeID",
    "HomelabContainerVolumeArgs",
    "HomelabContainerVolumeProvisionedSource",
    "HomelabHTTPSDeploymentIngressArgs",
    "HomelabKubernetesDeployment",
    "HomelabKubernetesDeploymentArgs",
    "HomelabKubernetesPersistentVolume",
    "HomelabKubernetesPersistentVolumeArgs",
    "HomelabKubernetesReferencePersistentVolume",
    "HomelabKubernetesReferencePersistentVolumeArgs",
    "HomelabPersistentVolume",
    "HomelabPersistentVolumeClaim",
    "HomelabService",
    "ImagePullCredential",
    "ImagePullSecretProvider",
    "namespace",
    "service_domain",
    "service_fqdn",
    "uid_gid",
]
