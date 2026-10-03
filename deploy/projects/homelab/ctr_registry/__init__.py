"""
projects.homelab.ctr_registry
=============================

This module defines the homelab container registry project and provides
an ImagePullSecretProvider that enables image pulls from the registry.
"""

from .imagepull import HomelabContainerRegistryImagePullSecretProvider
from .project import HomelabContainerRegistryProject

__all__ = [
    "HomelabContainerRegistryImagePullSecretProvider",
    "HomelabContainerRegistryProject",
]
