"""
tests/conftest -- Global Test Fixtures and Configuration
========================================================

This file contains global test fixtures and configuration.
"""

from os import SEEK_SET
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from textwrap import dedent
from typing import Generator

import pytest

from infralib import (
    InfrastructureConfiguration,
    LocalBackendProvider,
)
from infralib.config.aws import AWSAccount, AWSOrganization
from infralib.config.domain import Domain
from infralib.config.gcp import GCPOrganization
from infralib.config.homelab import Homelab
from infralib.config.notification import (
    EmailChannel,
    NotificationCategory,
    NotificationChannels,
)


@pytest.fixture
def local_backend_dir() -> Generator[Path]:
    """
    Returns the path to a temporary directory suitable for use as a local backend.

    The directory is cleaned up at fixture teardown time.
    """
    d = TemporaryDirectory(
        prefix="infralib-test-local-backend-", delete=False, ignore_cleanup_errors=True
    )
    d_path = Path(d.name)
    sentinel_path = d_path / LocalBackendProvider.SENTINEL_FILE_NAME
    sentinel_path.touch()

    yield d_path

    d.cleanup()


@pytest.fixture
def local_backend_provider(local_backend_dir: Path) -> LocalBackendProvider:
    """
    Returns a LocalBackendProvider whose backend points at a temporary directory.

    The backend is cleaned up at fixture teardown time.
    """
    return LocalBackendProvider(local_backend_dir)


@pytest.fixture
def test_infrastructure_configuration() -> InfrastructureConfiguration:
    """
    Returns a test infrastructure configuration containing dummy values.
    """
    domains = {
        "primary": Domain("primary", "test.example.com", "Primary domain"),
        "personal": Domain("personal", "personal.test.example.com", "Personal domain"),
    }
    aws_mgmt_account = AWSAccount("000000000777")
    aws_organization = AWSOrganization(
        organization_id="o-ooooooooid",
        root_ou_id="r-xxou",
        management_account=aws_mgmt_account,
        member_account_email_generator=lambda environment, function: (
            f"aws.{environment}.{function}@{domains['personal'].domain}"
        ),
        organization_account_access_role="MyRole",
        preferred_region="us-west-1",
        personal_iam_user="john.doe",
        infrastructure_manager_role="arn:aws:iam::000000000777:role/MyInfraRole",
    )
    gcp_organization = GCPOrganization(
        domain=domains["primary"].domain,
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
                email=f"billing@{domains['primary'].domain}",
            ),
            EmailChannel(
                name="Second Billing Test",
                category=NotificationCategory.CLOUD_BILLING,
                email=f"second.billing@{domains['primary'].domain}",
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


@pytest.fixture
def test_infrastructure_yaml_configuration() -> str:
    """
    Fixture defining a full, YAML-formatted InfrastructureConfiguration with
    sample values.
    """
    return dedent(
        """
        ---
        domains:
            - id:          primary
              domain:      test.example.com
              description: Primary domain

            - id:          personal
              domain:      personal.test.example.com
              description: Personal domain

        aws_organization:
            management_account:
                account_id: "000000000777"

            infrastructure_manager_role:      arn:aws:iam::000000000777:role/MyInfraRole
            organization_account_access_role: MyRole

            organization_id:       o-ooooooooid
            root_ou_id:            r-xxou
            preferred_region:      us-west-1
            personal_iam_user:     john.doe
            member_email_template: aws.{env}.{fn}@personal.test.example.com

        gcp_organization:
            domain:             test.example.com
            organization_id:    "000000000888"
            billing_account_id: "000000-000000-100001"
            preferred_region:   us-west2
            personal_iam_user:  john.doe@test.example.com
            quota_project:      my-quota-project

            infrastructure_manager_service_account: my-infra-sa@infra-mgmt-000000000888.iam.gserviceaccount.com

        homelab:
            kubernetes_context: k8stest

        notification_channels:
            - name: First Billing Test
              type: email
              category: cloud-billing
              email: billing@test.example.com
            - name: Second Billing Test
              type: email
              category: cloud-billing
              email: billing.second@test.example.com
    """.strip()
    )


@pytest.fixture
def test_infrastructure_yaml_configuration_path(
    test_infrastructure_yaml_configuration: str,
) -> Generator[Path]:
    """
    Returns the path to a named file containing test_yaml_config.
    """
    with NamedTemporaryFile(prefix="infralib-test-yaml-config-") as f:
        f.write(test_infrastructure_yaml_configuration.encode("utf-8"))
        f.seek(0, SEEK_SET)
        yield Path(f.name)
