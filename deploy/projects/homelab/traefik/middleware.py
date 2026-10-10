"""
projects.homelab.traefik.middleware
===================================

This module contains helper functions for Traefik middlewares.
"""

from dataclasses import dataclass

from pulumi import Input, Output, ResourceOptions
import pulumi_kubernetes as k8s
import pulumi_random as random

from infralib import InfrastructureComponent


@dataclass
class TraefikMiddlewareRef:
    """
    A reference to a Traefik Middleware.
    """

    namespace: Input[str]
    """
    The namespace that the Middleware resource is provisioned in.
    """

    name: Input[str]
    """
    The name of the Middleware resource.
    """

    def to_spec(self) -> dict[str, Input[str]]:
        return {
            "namespace": self.namespace,
            "name": self.name,
        }


@dataclass
class TraefikHTTPBasicAuthSecretArgs:
    """
    Arguments to create a kubernetes.io/basic-auth secret with a username
    and randomly generated password meeting the given criteria.
    """

    username: Input[str]
    """
    The HTTP basic authentication username.
    """

    password_args: random.RandomPasswordArgs
    """
    Arguments passed to the RandomPassword resource.

    The generated password is used for basic authentication.
    """


@dataclass
class TraefikHTTPBasicAuthMiddlewareArgs:
    """
    Arguments to TraefikHTTPBasicAuthMiddleware.
    """

    namespace: Input[str]
    """
    The Kubernetes namespace that the Traefik middleware is created in.
    """

    name: Input[str]
    """
    The Kubernetes name of the Traefik middleware resource.
    """

    secret: k8s.core.v1.LocalObjectReferenceArgs | TraefikHTTPBasicAuthSecretArgs
    """
    One of:
        * The name of the Kubernetes secret containing the basic auth credentials.
          The secret should be of type kubernetes.io/basic-auth.

        * Arguments defining a secret to be created.
    """


class TraefikHTTPBasicAuthMiddleware(
    InfrastructureComponent[TraefikHTTPBasicAuthMiddlewareArgs]
):
    """
    Infrastructure component that provisions a Traefik middleware providing
    HTTP basic authentication.
    """

    def provision(self) -> None:
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.k8s_ropts = self.default_ropts.merge(
            ResourceOptions(provider=k8s_provider)
        )

        self.secret: k8s.core.v1.Secret | None = None

        if isinstance(self.args.secret, k8s.core.v1.LocalObjectReferenceArgs):
            secret_name = self.args.secret.name
        elif isinstance(self.args.secret, TraefikHTTPBasicAuthSecretArgs):
            secret_name = self._provision_basic_auth_secret(self.args.secret)
        else:
            raise ValueError("secret is unsupported type")

        self.middleware = k8s.apiextensions.CustomResource(
            f"{self.name}_middleware",
            api_version="traefik.io/v1alpha1",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.args.namespace,
                name=self.args.name,
            ),
            kind="Middleware",
            spec={
                "basicAuth": {
                    "secret": secret_name,
                },
            },
            opts=self.k8s_ropts,
        )

    def _provision_basic_auth_secret(
        self,
        basic_auth_secret_args: TraefikHTTPBasicAuthSecretArgs,
    ) -> Output[str]:
        """
        Provisions a basic auth secret and returns the name of the created secret.
        """
        random_provider = self.dctx.provider_factory.random_provider()
        random_ropts = self.default_ropts.merge(
            ResourceOptions(provider=random_provider)
        )
        password = random.RandomPassword(
            f"{self.name}_password",
            args=basic_auth_secret_args.password_args,
            opts=random_ropts,
        )
        self.secret = k8s.core.v1.Secret(
            f"{self.name}_secret",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.args.namespace,
                name=f"traefik-middleware-{self.args.name}-basic-auth",
            ),
            type="kubernetes.io/basic-auth",
            string_data={
                "username": basic_auth_secret_args.username,
                "password": password.result,
            },
            opts=self.k8s_ropts,
        )
        return self.secret.metadata.name

    def ref(self) -> TraefikMiddlewareRef:
        """
        Returns a TraefikMiddlewareRef that references this middleware.
        """
        return TraefikMiddlewareRef(
            namespace=self.middleware.metadata.namespace,  # type: ignore
            name=self.middleware.metadata.name,  # type: ignore
        )
