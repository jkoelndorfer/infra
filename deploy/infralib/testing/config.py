"""
infralib/testing/config -- Dummy Infrastructure Configuration
=============================================================

This module contains the dummy configuration that renders and tests use. Rendered
output is committed to the repository, so these values must never be real.
"""

from ..config import InfrastructureConfiguration
from ..config.aws import AWSAccount, AWSOrganization
from ..config.domain import Domain, DKIMv1
from ..config.gcp import GCPOrganization
from ..config.homelab import Homelab
from ..config.notification import (
    EmailChannel,
    NotificationCategory,
    NotificationChannels,
)


def dummy_infrastructure_configuration() -> InfrastructureConfiguration:
    """
    Returns an infrastructure configuration containing dummy values.
    """
    domains = {
        "primary": Domain(
            id="primary",
            domain="test.example.com",
            description="Primary domain",
            dkim_v1=[
                DKIMv1("test1", "rsa", "test1_public_key"),
                DKIMv1("test2", "ed25519", "test2_public_key"),
            ],
            google_site_verification="primary_verification",
        ),
        "personal": Domain(
            id="personal",
            domain="personal.test.example.com",
            description="Personal domain",
            dkim_v1=[],
            google_site_verification="personal_verification",
        ),
        "personal_legacy": Domain(
            id="personal_legacy",
            domain="legacy.test.example.com",
            description="Legacy personal domain",
            dkim_v1=[],
            google_site_verification="personal_legacy_verification",
        ),
        "anon": Domain(
            id="anon",
            domain="anon.test.example.com",
            description="Anonymous domain",
            dkim_v1=[],
            google_site_verification="anon_verification",
        ),
        "homelab": Domain(
            id="homelab",
            domain="homelab.test.example.com",
            description="Homelab domain",
            dkim_v1=[],
            google_site_verification="homelab_verification",
        ),
    }
    aws_mgmt_account = AWSAccount("000000000777")
    aws_organization = AWSOrganization(
        organization_id="o-ooooooooid",
        root_ou_id="r-xxou",
        management_account=aws_mgmt_account,
        member_account_email_generator=lambda environment, function: (
            f"aws.{environment}.{function}@{domains['personal']._domain}"
        ),
        organization_account_access_role="MyRole",
        preferred_region="us-west-1",
        personal_iam_user="john.doe",
        infrastructure_manager_role="arn:aws:iam::000000000777:role/MyInfraRole",
        sso_user="john.doe@personal.test.example.com",
    )
    gcp_organization = GCPOrganization(
        domain=domains["primary"]._domain,
        organization_id="000000000888",
        billing_account_id="000000-000000-100001",
        preferred_region="us-west2",
        personal_iam_user="john.doe@test.example.com",
        infrastructure_manager_service_account="my-infra-sa@infra-mgmt-000000000888.iam.gserviceaccount.com",
        quota_project="my-quota-project",
    )
    homelab = Homelab(
        kubernetes_context="k8stest",
    )
    notification_channels = NotificationChannels(
        [
            EmailChannel(
                name="First Billing Test",
                category=NotificationCategory.CLOUD_BILLING,
                email=f"billing@{domains['primary']._domain}",
            ),
            EmailChannel(
                name="Second Billing Test",
                category=NotificationCategory.CLOUD_BILLING,
                email=f"second.billing@{domains['primary']._domain}",
            ),
        ]
    )
    return InfrastructureConfiguration(
        domains=domains,
        aws_organization=aws_organization,
        gcp_organization=gcp_organization,
        homelab=homelab,
        notification_channels=notification_channels,
    )
