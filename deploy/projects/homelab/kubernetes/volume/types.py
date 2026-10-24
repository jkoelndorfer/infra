"""
projects.homelab.kubernetes.volume.types
========================================

This module contains type definitions for persistent volume fields used
by Kubernetes.
"""

from typing import Literal

AccessMode = Literal[
    "ReadWriteOnce",
    "ReadOnlyMany",
    "ReadWriteMany",
    "ReadWriteOncePod",
]
VolumeReclaimPolicy = Literal["Retain", "Recycle", "Delete"]
