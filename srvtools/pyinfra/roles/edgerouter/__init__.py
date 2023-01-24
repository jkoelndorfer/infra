"""
roles/edgerouter
----------------

This module contains the edgerouter role.

It configures my home Ubiquiti EdgeRouter 6P as appropriate.
"""

from .build import build
from .provision import provision

__all__ = [
    "build",
    "provision",
]
