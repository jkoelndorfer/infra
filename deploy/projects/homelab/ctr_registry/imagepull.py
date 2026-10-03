"""
projects.homelab.ctr_registry.imagepull
=======================================

This module contains an ImagePullSecretProvider that provides secrets
for this container registry.
"""

from infralib import DeploymentContext
from typing import Sequence

from pulumi import Input

from ..kubernetes.imagepull import (
    ImagePullCredential,
    ImagePullSecretProvider,
)
from .project import HomelabContainerRegistryProject


class HomelabContainerRegistryImagePullSecretProvider(ImagePullSecretProvider):
    """
    ImagePullSecretProvider which provides image pull secrets for the homelab
    container registry.
    """

    project = HomelabContainerRegistryProject

    def credentials(
        self,
        dctx: DeploymentContext,
        image: str,
    ) -> Sequence[Input[ImagePullCredential]]:
        image_fqdn = image.split("/")[0].strip()
        cred_list: list[ImagePullCredential] = list()
        for target in self.project.deployment_targets():
            for access in self.project.access_levels:
                registry_fqdn = self.project.registry_fqdn(dctx, access, target)
                if image_fqdn == registry_fqdn:
                    outputs = dctx.outputs(self.project.stack(target))
                    creds = outputs["credentials"].value
                    cred_list.append(
                        ImagePullCredential(
                            hostname=registry_fqdn,
                            username=creds["username"],
                            password=creds["password"],
                        )
                    )

        return cred_list
