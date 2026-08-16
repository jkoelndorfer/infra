"""
projects.homelab.kubernetes.service
===================================

This module contains the definition for a homelab Kubernetes service
and supporting types.
"""

from dataclasses import dataclass


@dataclass
class HomelabService:
    """
    Representation of a published homelab service.
    """

    service_name: str
    """
    The name of the Kubernetes service that serves the default route.
    """

    container_port: int
    """
    The port that the container receives HTTP traffic on.
    """

    hostname: str
    """
    The service's default hostname. This is the first part of the fully-qualified
    domain name. It excludes the domain.
    """

    domain: str
    """
    The second part of the fully-qualified domain name. It excludes the hostname.
    """

    @property
    def fqdn(self) -> str:
        """
        Returns this service's fully-qualified domain name.
        """
        return f"{self.hostname}.{self.domain}"
