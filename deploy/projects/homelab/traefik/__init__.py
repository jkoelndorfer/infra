"""
projects.homelab.traefik
========================

This module contains the homelab Traefik project.
"""

from .config import TraefikConfiguration
from .project import HomelabTraefikProject
from .route import (
    default_route_transformer,
    TraefikIngressRoute,
    TraefikIngressRouteArgs,
    TraefikIngressRouteSpecRoute,
    TraefikIngressRouteTLSDomain,
    TraefikMiddlewareRef,
    TraefikRouteBuilder,
    TraefikRouteTransformer,
    TraefikServiceRef,
)


__all__ = [
    "default_route_transformer",
    "HomelabTraefikProject",
    "TraefikConfiguration",
    "TraefikMiddlewareRef",
    "TraefikIngressRoute",
    "TraefikIngressRouteArgs",
    "TraefikIngressRouteSpecRoute",
    "TraefikIngressRouteTLSDomain",
    "TraefikRouteBuilder",
    "TraefikRouteTransformer",
    "TraefikServiceRef",
]
