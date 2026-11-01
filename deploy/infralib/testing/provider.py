"""
infralib/testing/provider -- Mock Provider Factory
==================================================

This module contains a ProviderFactory for use under Pulumi's mock runtime.
"""

import pulumi_aws as aws
import pulumi_command as command
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s
import pulumi_random as random

from ..pulumi.provider import KubernetesClientModule, ProviderFactory
from .kubernetes import FakeKubernetesClient


class MockProviderFactory(ProviderFactory):
    """
    ProviderFactory that registers real provider resources, which only reach the
    mock runtime, and that returns a fake Kubernetes client.

    Providers are cached by logical name, as StandardProviderFactory caches them,
    because Pulumi rejects duplicate URNs.
    """

    def __init__(self, kubernetes_client: KubernetesClientModule | None = None) -> None:
        self._kubernetes_client = kubernetes_client or FakeKubernetesClient()
        self._aws: dict[str, aws.Provider] = {}
        self._command: dict[str, command.Provider] = {}
        self._gcp: dict[str, gcp.Provider] = {}
        self._k8s: dict[str, k8s.Provider] = {}
        self._random: dict[str, random.Provider] = {}

    def aws_provider(
        self,
        name: str,
        assume_role_arn: str | None = None,
        region: str | None = None,
        profile: str | None = None,
    ) -> aws.Provider:
        """
        Returns a mock AWS provider.
        """
        if name not in self._aws:
            self._aws[name] = aws.Provider(name, region=region, profile=profile)
        return self._aws[name]

    def command_provider(self, name: str = "command") -> command.Provider:
        """
        Returns a mock Command provider.
        """
        if name not in self._command:
            self._command[name] = command.Provider(name)
        return self._command[name]

    def gcp_provider(self, name: str = "gcp") -> gcp.Provider:
        """
        Returns a mock GCP provider.
        """
        if name not in self._gcp:
            self._gcp[name] = gcp.Provider(name)
        return self._gcp[name]

    def kubernetes_client(self) -> KubernetesClientModule:
        """
        Returns the fake Kubernetes client.
        """
        return self._kubernetes_client

    def kubernetes_provider(self, name: str = "kubernetes") -> k8s.Provider:
        """
        Returns a mock Kubernetes provider.
        """
        if name not in self._k8s:
            self._k8s[name] = k8s.Provider(name)
        return self._k8s[name]

    def random_provider(self, name: str = "random") -> random.Provider:
        """
        Returns a mock Random provider.
        """
        if name not in self._random:
            self._random[name] = random.Provider(name)
        return self._random[name]
