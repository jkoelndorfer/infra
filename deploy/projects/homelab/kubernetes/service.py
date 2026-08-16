"""
projects.homelab.kubernetes.service
===================================

This module contains the definition for a homelab Kubernetes service
and supporting types.
"""

from dataclasses import dataclass

from infralib import DeploymentContext


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


def service_domain(dctx: DeploymentContext) -> str:
    """
    Returns the homelab domain for a particular deployment context.
    """
    return dctx.config.domains["homelab"].domain_for(dctx.target)


def service_fqdn(dctx: DeploymentContext, hostname: str) -> str:
    """
    Returns a service's FQDN given a deployment context and hostname.
    """
    return f"{hostname}.{service_domain(dctx)}"
