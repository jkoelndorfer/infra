"""
provision/roles/edgerouter -- EdgeRouter Role
=============================================

This role configures my home Ubiquiti EdgeRouter 6P.
"""

from .provision import provision

__all__ = [
    "provision",
]
