"""
projects.homelab.route
======================

This module contains helper functions for Traefik ingress routes.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol, Sequence

from pulumi import Input

from ..kubernetes.service import HomelabService


@dataclass
class TraefikServiceRef:
    name: Input[str]
    port: Input[int]
    kind: Input[Literal["Service"]] = "Service"


@dataclass
class TraefikMiddlewareRef:
    namespace: Input[str]
    name: Input[str]


@dataclass
class TraefikIngressRouteSpecRoute:
    match: Input[str]
    services: Input[Sequence[Input[TraefikServiceRef]]]
    middlewares: Input[Sequence[Input[TraefikMiddlewareRef]]] = field(
        default_factory=list
    )
    priority: Input[int] = 0
    kind: Input[Literal["Rule"]] = "Rule"


class TraefikRouteTransformer(Protocol):
    def __call__(
        self,
        service: HomelabService,
        default_routes: Sequence[TraefikIngressRouteSpecRoute],
    ) -> Sequence[TraefikRouteSpec]:
        """
        Optionally transforms the given set of Traefik routes.
        """
        raise NotImplementedError("protocol does not provide an implementation")


def default_route(s: HomelabService) -> TraefikRouteSpec:
    """
    Returns the default route for a given HomelabService.
    """
    return TraefikRouteSpec(
        match=default_host_match(s),
        priority=0,
        services=[
            TraefikServiceRef(
                name=s.service_name,
                port=s.container_port,
                kind="Service",
            )
        ],
    )


def default_host_match(s: HomelabService) -> str:
    """
    Returns the default, host-based match for a given HomelabService.
    """
    return f"Host(`{s.fqdn}`)"
