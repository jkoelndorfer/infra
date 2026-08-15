"""
projects.homelab.traefik
========================

This module contains the homelab Traefik project.
"""

from .config import TraefikConfiguration
from .middleware import (
    TraefikHTTPBasicAuthMiddleware,
    TraefikHTTPBasicAuthMiddlewareArgs,
    TraefikHTTPBasicAuthSecretArgs,
    TraefikMiddlewareRef,
)
from .ingress import (
    TraefikOnlyIngressPolicy,
    TraefikOnlyIngressPolicyArgs,
)
from .project import HomelabTraefikProject
from .route import (
    default_route_transformer,
    TraefikIngressRoute,
    TraefikIngressRouteArgs,
    TraefikIngressRouteSpecRoute,
    TraefikIngressRouteTLSDomain,
    TraefikRouteBuilder,
    TraefikRouteTransformer,
    TraefikServiceRef,
)


__all__ = [
    "default_route_transformer",
    "HomelabTraefikProject",
    "TraefikConfiguration",
    "TraefikHTTPBasicAuthMiddleware",
    "TraefikHTTPBasicAuthMiddlewareArgs",
    "TraefikHTTPBasicAuthSecretArgs",
    "TraefikIngressRoute",
    "TraefikIngressRouteArgs",
    "TraefikIngressRouteSpecRoute",
    "TraefikIngressRouteTLSDomain",
    "TraefikMiddlewareRef",
    "TraefikOnlyIngressPolicy",
    "TraefikOnlyIngressPolicyArgs",
    "TraefikRouteBuilder",
    "TraefikRouteTransformer",
    "TraefikServiceRef",
]
