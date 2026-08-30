"""
projects.dns
============

This module contains InfrastructureProjects that configure DNS.
"""

from .zones import DNSZonesProject, DNSZone

__all__ = [
    "DNSZone",
    "DNSZonesProject",
]
