"""
projects.homelab.kubernetes.network_policy
==========================================

This module contains helpers for NetworkPolicies that admit clients from outside the
cluster.
"""

import pulumi_kubernetes as k8s

from infralib.config.homelab import HomelabNetworking

# The labels of homelab.vpn's wg-easy pods, and of their namespace. They are spelled
# out because homelab.vpn depends on homelab.traefik, which uses this module.
_VPN_NAMESPACE_LABELS = {"local/name": "vpn"}
_VPN_POD_LABELS = {"service-name": "vpn"}


def trusted_plus_peers(
    networking: HomelabNetworking,
) -> list[k8s.networking.v1.NetworkPolicyPeerArgs]:
    """
    Returns the peers that make up trusted+: the networks in the router's
    ADDR_TRUSTED_PLUS group, and VPN peers. wg-easy masquerades VPN peers' traffic as
    its pod's address, so they are admitted by selecting its pods rather than by the
    wireguard_trusted network.

    These only match traffic that keeps its client's address, such as traffic arriving
    through a host port.
    """
    networks = networking.networks
    return [
        *[
            k8s.networking.v1.NetworkPolicyPeerArgs(
                ip_block=k8s.networking.v1.IPBlockArgs(cidr=str(n.ipv4_network)),
            )
            for n in [
                networks.mgmt,
                networks.mgmt_backup,
                networks.infra,
                networks.trusted,
            ]
        ],
        k8s.networking.v1.NetworkPolicyPeerArgs(
            namespace_selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels=_VPN_NAMESPACE_LABELS,
            ),
            pod_selector=k8s.meta.v1.LabelSelectorArgs(
                match_labels=_VPN_POD_LABELS,
            ),
        ),
    ]
