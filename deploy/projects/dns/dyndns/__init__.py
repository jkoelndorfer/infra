"""
projects.dns.dyndns
===================

This module contains the InfrastructureProject that provides dynamic DNS.
"""

from .project import DNSDynDNSProject, DynDNSClient

__all__ = [
    "DNSDynDNSProject",
    "DynDNSClient",
]
