"""
projects.homelab.traefik.ingress
================================

This module contains helpers to define a Traefik ingress policy for
services that are reverse-proxied by Traefik.
"""

from dataclasses import dataclass

from pulumi import Input, Output
import pulumi_kubernetes as k8s

from infralib import InfrastructureComponent


@dataclass
class TraefikOnlyIngressPolicyArgs:
    """
    Arguments applied to a Traefik-only ingress policy.
    """

    namespace: Input[str]
    """
    The namespace that the Traefik-only policy is applied in.
    """

    name: Input[str]
    """
    The name prefix of this Traefik-only ingress policy.
    """

    port: Input[str | int]
    """
    The port that this policy applies to.
    """

    pod_label_selector: k8s.meta.v1.LabelSelectorArgs
    """
    Label selectors used to identify the pod(s) that this policy applies to.
    """


class TraefikOnlyIngressPolicy(InfrastructureComponent[TraefikOnlyIngressPolicyArgs]):
    """
    Resource that permits ingress only via Traefik.
    """

    def provision(self) -> None:
        traefik_peer = k8s.networking.v1.NetworkPolicyPeerArgs(
            namespace_selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels={
                    "local/name": "traefik",
                },
            ),
        )
        traefik_ingress_rule = k8s.networking.v1.NetworkPolicyIngressRuleArgs(
            from_=[traefik_peer],
            ports=[
                k8s.networking.v1.NetworkPolicyPortArgs(
                    port=self.args.port,
                )
            ],
        )

        self.policy = k8s.networking.v1.NetworkPolicy(
            f"{self.name}_traefik_only",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.args.namespace,
                name=Output.from_input(self.args.name).apply(
                    lambda n: f"{n}-traefik-only"
                ),
            ),
            spec=k8s.networking.v1.NetworkPolicySpecArgs(
                pod_selector=self.args.pod_label_selector,
                policy_types=["Ingress"],
                ingress=[traefik_ingress_rule],
            ),
            opts=self.default_ropts,
        )
