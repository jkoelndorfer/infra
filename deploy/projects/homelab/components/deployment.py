"""
projects.homelab.components.deployment
======================================

This module contains the InfrastructureComponent for a
standard homelab deployment.
"""

from pulumi import (
    Input,
    input_type,
    Output,
    output_type,
)
import pulumi_kubernetes as k8s

from infralib.pulumi.component import InfrastructureComponent


@output_type
class Namespace:
    """
    Output type representing a Kubernetes namespace.
    """

    name: Output[str]

    def __init__(self, name: Output[str]) -> None:
        self.name = name


@input_type
class HomelabDeploymentArgs:
    """
    Set of arguments passed to a HomelabDeployment.

    name:    The name of the deployment. This is included in the created namespace.
    uid_gid: The UID/GID assigned to this deployment.
    """

    def __init__(
        self,
        name: Input[str],
        uid_gid: Input[int],
    ) -> None:
        self.name = name
        self.uid_gid = uid_gid


class HomelabDeployment(InfrastructureComponent[HomelabDeploymentArgs]):
    namespace: Output[Namespace]

    def provision(self) -> None:
        namespace = k8s.core.v1.Namespace(
            "namespace",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                name=Output.format(
                    "{0}-{1}", self.dctx.target.environment, self.args.name
                ),
            ),
            opts=self.default_ropts,
        )
        self.output("namespace", namespace.metadata["name"])
        self.output("uid_gid", Output.from_input(self.args.uid_gid))
