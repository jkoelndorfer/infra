"""
roles/miniserv
--------------

This module contains the miniserv role.

It configures a Raspberry Pi to provide self-hosted services at home.
"""

from .build import build
from .provision import provision

__all__ = [
    "build",
    "provision",
]
