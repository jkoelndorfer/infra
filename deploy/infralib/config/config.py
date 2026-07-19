"""
infralib/config/config -- Infrastructure Configuration
======================================================

This file defines configuration that is made available to Pulumi and pyinfra executions.
"""

from .aws import AWSOrganization
from .domain import Domains
from .gcp import GCPOrganization
from .notification import NotificationChannels


class InfrastructureConfiguration:
    """
    Infrastructure configuration made available in every execution context.
    """

    def __init__(
        self,
        domains: Domains,
        aws_organization: AWSOrganization,
        gcp_organization: GCPOrganization,
        notification_channels: NotificationChannels,
    ) -> None:
        # A dictionary containing a set of DNS domains. Domains are
        # referenced by ID.
        self.domains = domains

        # The AWS organization that infrastructure is deployed to.
        self.aws_organization = aws_organization

        # The GCP organization that infrastructure is deployed to.
        self.gcp_organization = gcp_organization

        # Channels by which notifications are sent.
        self.notification_channels = notification_channels
