"""
infralib/config/config -- Infrastructure Configuration
======================================================

This file defines configuration that is made available to Pulumi and pyinfra executions.
"""

from .aws import AWSOrganization
from .gcp import GCPOrganization


class InfrastructureConfiguration:
    """
    Infrastructure configuration made available in every execution context.
    """

    def __init__(
        self,
        primary_domain: str,
        personal_domain: str,
        aws_organization: AWSOrganization,
        gcp_organization: GCPOrganization,
    ) -> None:
        # The primary domain used to establish an Internet presence for my household.
        self.primary_domain = primary_domain

        # The domain used for my personal Internet presence.
        self.personal_domain = personal_domain

        # The AWS organization that infrastructure is deployed to.
        self.aws_organization = aws_organization

        # The GCP organization that infrastructure is deployed to.
        self.gcp_organization = gcp_organization
