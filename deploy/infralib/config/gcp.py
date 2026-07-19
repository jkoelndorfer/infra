"""
infralib/config/gcp -- GCP Configuration
========================================

This file defines data types for GCP-specific configuration.
"""

from typing import Self


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
        personal_iam_user: str,
        infrastructure_manager_service_account: str,
        quota_project: str,
    ) -> None:
        # The domain of the GCP organization.
        self.domain = domain

        # The GCP organization's numerical organization ID.
        self.organization_id = organization_id

        # The primary billing account ID used within the organization.
        self.billing_account_id = billing_account_id

        # The preferred region to deploy infrastructure in.
        self.preferred_region = preferred_region

        # The IAM user used for day-to-day administration.
        self.personal_iam_user = personal_iam_user

        # Service account that is impersonated to make infrastructure changes.
        self.infrastructure_manager_service_account = (
            infrastructure_manager_service_account
        )

        # Default project used for quotas.
        self.quota_project = quota_project

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Self:
        return cls(
            d["domain"],
            d["organization_id"],
            d["billing_account_id"],
            d["preferred_region"],
            d["personal_iam_user"],
            d["infrastructure_manager_service_account"],
            d["quota_project"],
        )
