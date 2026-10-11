"""
projects.homelab.route
======================

This module contains helper functions for Traefik ingress routes.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, Sequence

from pulumi import Input
import pulumi_kubernetes as k8s

from infralib import InfrastructureComponent

from ..kubernetes.service import HomelabService
from .config import TraefikConfiguration as config
from .middleware import TraefikMiddlewareRef


@dataclass
class TraefikServiceRef:
    name: Input[str]
    port: Input[int]
    kind: Input[Literal["Service"]] = "Service"

    def to_spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "port": self.port,
            "kind": self.kind,
        }


@dataclass
class TraefikIngressRouteSpecRoute:
    match: Input[str]
    services: Sequence[TraefikServiceRef]
    middlewares: Sequence[TraefikMiddlewareRef] = field(default_factory=list)
    priority: Input[int] = 0
    kind: Input[Literal["Rule"]] = "Rule"

    def to_spec(self) -> dict[str, Any]:
        return {
            "match": self.match,
            "services": [s.to_spec() for s in self.services],
            "middlewares": [m.to_spec() for m in self.middlewares],
            "priority": self.priority,
            "kind": self.kind,
        }


@dataclass
class TraefikIngressRouteTLSDomain:
    main: Input[str]
    sans: Input[Sequence[Input[str]]]

    def to_spec(self) -> dict[str, Any]:
        return {
            "main": self.main,
            "sans": self.sans,
        }


@dataclass
class TraefikIngressRouteArgs:
    namespace: Input[str]
    name: Input[str]
    routes: Sequence[TraefikIngressRouteSpecRoute]
    tls_domains: Sequence[TraefikIngressRouteTLSDomain]
    tls_cert_resolver: str = config.cert_resolver


class TraefikRouteBuilder:
    """
    Factory that produces Traefik IngressRoute configuration.
    """

    def __init__(
        self,
        homelab_service: HomelabService,
    ) -> None:
        self.homelab_service = homelab_service

    @property
    def default_host_match(self) -> str:
        """
        Returns the default, host-based match.
        """
        return f"Host(`{self.homelab_service.fqdn}`)"

    def route(
        self,
        match: str | None = None,
        priority: int = 0,
        services: list[TraefikServiceRef] | None = None,
        middlewares: list[TraefikMiddlewareRef] | None = None,
    ) -> TraefikIngressRouteSpecRoute:
        """
        Returns a new route.

        Route defaults are substituted for unspecified arguments.
        """
        return TraefikIngressRouteSpecRoute(
            match=match or self.default_host_match,
            priority=priority,
            middlewares=middlewares or [],
            services=services
            or [
                TraefikServiceRef(
                    name=self.homelab_service.service_name,
                    port=self.homelab_service.container_port,
                    kind="Service",
                ),
            ],
        )


class TraefikRouteTransformer(Protocol):
    def __call__(
        self,
        builder: TraefikRouteBuilder,
        default_routes: Sequence[TraefikIngressRouteSpecRoute],
    ) -> Sequence[TraefikIngressRouteSpecRoute]:
        """
        Optionally transforms the given set of Traefik routes.
        """
        raise NotImplementedError("protocol does not provide an implementation")


def default_route_transformer(
    builder: TraefikRouteBuilder,
    default_routes: Sequence[TraefikIngressRouteSpecRoute],
) -> Sequence[TraefikIngressRouteSpecRoute]:
    return default_routes


class TraefikIngressRoute(InfrastructureComponent[TraefikIngressRouteArgs]):
    """
    Component that provisions a Traefik IngressRoute in accordance with
    homelab standards.
    """

    def provision(self) -> None:
        self.ingress_route = k8s.apiextensions.CustomResource(
            f"{self.name}_ingress_route",
            api_version="traefik.io/v1alpha1",
            kind="IngressRoute",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.args.namespace,
                name=self.args.name,
            ),
            spec={
                "routes": [r.to_spec() for r in self.args.routes],
                "tls": {
                    "certResolver": self.args.tls_cert_resolver,
                    "domains": [d.to_spec() for d in self.args.tls_domains],
                },
            },
            opts=self.default_ropts,
        )
