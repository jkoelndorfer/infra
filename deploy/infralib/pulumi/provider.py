"""
infralib/pulumi/provider -- Pulumi Providers
============================================

This module contains code to construct standardized Pulumi providers.
"""

from abc import ABC, abstractmethod
from typing import Callable, Protocol, TypeVar, TYPE_CHECKING

import kubernetes
import pulumi_aws as aws
import pulumi_command as command
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s
import pulumi_random as random

if TYPE_CHECKING:
    from ..deployment.context import DeploymentContext


T = TypeVar("T")


class KubernetesClientModule(Protocol):
    """
    Protocol describing the Kubernetes client module.
    """

    AppsV1Api: type[kubernetes.client.AppsV1Api]
    CoreV1Api: type[kubernetes.client.CoreV1Api]


class ProviderFactory(ABC):
    """
    Abstract base class defining a Pulumi provider factory.
    """

    @abstractmethod
    def aws_provider(
        self,
        name: str,
        assume_role_arn: str | None = None,
        region: str | None = None,
        profile: str | None = None,
    ) -> aws.Provider:
        """
        Returns an AWS provider that assumes the given role and defaults to
        creating resources in the given region.
        """

    @abstractmethod
    def command_provider(self, name: str = "command") -> command.Provider:
        """
        Returns a Command provider.
        """

    @abstractmethod
    def gcp_provider(self, name: str = "gcp") -> gcp.Provider:
        """
        Returns a GCP provider.
        """

    @abstractmethod
    def kubernetes_client(
        self,
    ) -> KubernetesClientModule:
        """
        Returns a reference to the Kubernetes client module, allowing
        instantiation of select Kubernetes API clients.
        """

    @abstractmethod
    def kubernetes_provider(self, name: str = "kubernetes") -> k8s.Provider:
        """
        Returns a Kubernetes provider.
        """

    @abstractmethod
    def random_provider(self, name: str = "random") -> random.Provider:
        """
        Returns a Random provider.
        """


class ProviderFactoryFactory(Protocol):
    """
    Protocol describing a function that creates a ProviderFactory.
    """

    def __call__(self, dctx: DeploymentContext) -> ProviderFactory:
        raise NotImplementedError("protocol does not provide a concrete implementation")


class StandardProviderFactory(ProviderFactory):
    """
    Standard factory for Pulumi providers. Providers are constructed with
    reasonable defaults.
    """

    def __init__(
        self,
        dctx: DeploymentContext,
        aws_preferred_region: str,
        gcp_quota_project: str,
        kubernetes_default_context: str,
        aws_default_profile: str = "default",
        aws_base_assume_role: str | None = None,
        gcp_impersonate_service_account: str | None = None,
    ) -> None:  # pragma: no cover
        self.dctx = dctx
        self.aws_preferred_region = aws_preferred_region
        self.aws_default_profile = aws_default_profile
        self.aws_base_assume_role = aws_base_assume_role
        self.gcp_impersonate_service_account = gcp_impersonate_service_account
        self.gcp_quota_project = gcp_quota_project
        self.kubernetes_default_context = kubernetes_default_context

    def aws_provider(
        self,
        name: str = "aws",
        assume_role_arn: str | None = None,
        region: str | None = None,
        profile: str | None = None,
    ) -> aws.Provider:  # pragma: no cover
        assume_roles: list[aws.ProviderAssumeRoleArgs] = list()
        for r in [self.aws_base_assume_role, assume_role_arn]:
            if r is None:
                continue
            assume_roles.append(
                aws.ProviderAssumeRoleArgs(
                    duration="20m",
                    role_arn=r,
                    session_name="infralib-pulumi",
                )
            )

        def make_aws_provider() -> aws.Provider:
            return aws.Provider(
                name,
                assume_roles=assume_roles,
                profile=profile or self.aws_default_profile,
                region=region or self.aws_preferred_region,
            )

        return self._try_cached_provider(
            f"aws:{assume_role_arn or '(none)'}:{region or '(none)'}:{profile or '(none)'}",
            make_aws_provider,
        )

    def command_provider(
        self, name: str = "command"
    ) -> command.Provider:  # pragma: no cover
        return self._try_cached_provider(
            f"command:{name}", lambda: command.Provider(name)
        )

    def gcp_provider(
        self, name: str = "gcp", project: str | None = None
    ) -> gcp.Provider:  # pragma: no cover
        def make_gcp_provider() -> gcp.Provider:
            return gcp.Provider(
                name,
                billing_project=self.gcp_quota_project,
                project=project,
                impersonate_service_account=self.gcp_impersonate_service_account,
                user_project_override=True,
            )

        return self._try_cached_provider(
            f"gcp:{name}:{project or '(none)'}",
            make_gcp_provider,
        )

    def kubernetes_client(
        self,
    ) -> KubernetesClientModule:  # pragma: no cover
        kubernetes.config.load_kube_config(context=self.kubernetes_default_context)

        return kubernetes.client  # type: ignore

    def kubernetes_provider(
        self, name: str = "kubernetes"
    ) -> k8s.Provider:  # pragma: no cover
        def make_k8s_provider() -> k8s.Provider:
            return k8s.Provider(
                name,
                context=self.kubernetes_default_context,
                enable_server_side_apply=True,
            )

        return self._try_cached_provider(
            f"k8s:{name}",
            make_k8s_provider,
        )

    def random_provider(
        self,
        name: str = "random",
    ) -> random.Provider:  # pragma: no cover
        return self._try_cached_provider(
            f"random:{name}", lambda: random.Provider(name)
        )

    def _try_cached_provider(
        self, key: str, factory: Callable[[], T]
    ) -> T:  # pragma: no cover
        full_key = f"StandardProviderFactory:{key}"
        provider: T | None = None
        provider = self.dctx.kv_get(full_key)

        if provider is None:
            provider = factory()
            self.dctx.kv_set(full_key, provider)

        return provider
