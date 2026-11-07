"""
provision/roles/kserv -- kserv Role
===================================

This role configures kserv, the homelab's Kubernetes host. It runs k3s in a Podman
container, and every service runs on k3s.
"""

from .provision import provision

__all__ = [
    "provision",
]
