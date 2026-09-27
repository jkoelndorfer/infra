"""
projects.homelab.kubernetes.imagepull
=====================================

This module contains helpers for providing image pull secrets to deployments.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from typing import Sequence

from pulumi import Input, Output, ResourceOptions
import pulumi_kubernetes as k8s

from infralib import DeploymentContext


@dataclass
class ImagePullCredential:
    """
    Class representing a credential used to pull container images
    from a registry.
    """

    hostname: str
    username: str
    password: str


class ImagePullSecretProvider(ABC):
    """
    Protocol defining a callable that can provide image pull secrets.
    """

    @abstractmethod
    def credentials(
        self,
        dctx: DeploymentContext,
        image: str,
    ) -> Sequence[Input[ImagePullCredential]]:
        """
        Given a deployment context and an image, returns credentials to permit
        pulling that image from the image's registry, if they are known.

        To create and return a secret, use secret().
        """

    def secret(
        self,
        name: str,
        dctx: DeploymentContext,
        namespace: Input[str],
        image: str,
        secret_name: Input[str] = "image-pull",
    ) -> k8s.core.v1.Secret | None:
        """
        Given a deployment context and an image, optionally provisions and
        returns a secret containing image pull credentials.
        """
        provider = dctx.provider_factory.kubernetes_provider()
        cache_key = f"ImagePullSecretProvider.{name}"
        secret: k8s.core.v1.Secret | None = dctx.kv_get(cache_key)

        if secret is not None:
            return secret

        credentials: Sequence[Input[ImagePullCredential]] = self.credentials(
            dctx, image
        )

        if not credentials:
            return None

        secret = k8s.core.v1.Secret(
            f"image_pull_{name}",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=namespace,
                name=secret_name,
            ),
            type="kubernetes.io/dockerconfigjson",
            string_data={
                ".dockerconfigjson": Output.all(*credentials).apply(
                    lambda creds: json.dumps(
                        {
                            "auths": {
                                c.hostname: {
                                    "username": c.username,
                                    "password": c.password,
                                }
                                for c in creds
                            },
                        },
                    ),
                ),
            },
            opts=ResourceOptions(provider=provider),
        )

        dctx.kv_set(cache_key, secret)

        return secret
