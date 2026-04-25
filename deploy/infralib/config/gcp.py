"""
infralib/config/gcp -- GCP Configuration
========================================

This file defines data types for GCP-specific configuration.
"""


class GCPOrganization:
    """
    Configuration representing a GCP organization.
    """

    def __init__(
        self,
        domain: str,
        organization_id: str,
        billing_account_id: str,
        preferred_region: str,
    ) -> None:
        # The domain of the GCP organization.
        self.domain = domain

        # The GCP organization's numerical organization ID.
        self.organization_id = organization_id

        # The primary billing account ID used within the organization.
        self.billing_account_id = billing_account_id

        # The preferred region to deploy infrastructure in.
        self.preferred_region = preferred_region
