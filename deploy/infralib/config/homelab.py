"""
infralib/config/homelab -- Homelab Configuration
================================================

This file defines data types for Homelab-specific configuration.
"""

from typing import Self


class Homelab:
    """
    Configuration for my homelab.
    """

    def __init__(self, kubernetes_context: str) -> None:
        # The Kubernetes context used to manage the homelab Kubernetes cluster.
        self.kubernetes_context = kubernetes_context

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Self:
        return cls(
            d["kubernetes_context"],
        )
