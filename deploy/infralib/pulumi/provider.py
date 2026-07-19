"""
infralib/pulumi/provider -- Pulumi Providers
============================================

This module contains code to construct standardized Pulumi providers.
"""

from abc import ABC, abstractmethod

import pulumi_aws as aws
import pulumi_command as command
import pulumi_gcp as gcp


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


class StandardProviderFactory(ProviderFactory):
    """
    Standard factory for Pulumi providers. Providers are constructed with
    reasonable defaults.
    """

    def __init__(
        self,
        aws_preferred_region: str,
        gcp_quota_project: str,
        aws_default_profile: str = "default",
        aws_base_assume_role: str | None = None,
        gcp_impersonate_service_account: str | None = None,
    ) -> None:
        self.aws_preferred_region = aws_preferred_region
        self.aws_default_profile = aws_default_profile
        self.aws_base_assume_role = aws_base_assume_role
        self.gcp_impersonate_service_account = gcp_impersonate_service_account
        self.gcp_quota_project = gcp_quota_project

    def aws_provider(
        self,
        name: str = "aws",
        assume_role_arn: str | None = None,
        region: str | None = None,
        profile: str | None = None,
    ) -> aws.Provider:
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

        return aws.Provider(
            name,
            assume_roles=assume_roles,
            profile=profile or self.aws_default_profile,
            region=region or self.aws_preferred_region,
        )

    def command_provider(self, name: str = "command") -> command.Provider:
        return command.Provider(name)

    def gcp_provider(
        self, name: str = "gcp", project: str | None = None
    ) -> gcp.Provider:
        return gcp.Provider(
            name,
            billing_project=self.gcp_quota_project,
            project=project,
            impersonate_service_account=self.gcp_impersonate_service_account,
            user_project_override=True,
        )
