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
from infralib.testing import dummy_infrastructure_configuration


@pytest.fixture(autouse=True)
def pulumi_config_passphrase(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Sets the Pulumi passphrase to a dummy value, so that tests behave the same
    regardless of the passphrase configured in the developer's environment.
    """
    monkeypatch.setenv("PULUMI_CONFIG_PASSPHRASE", "test")
    monkeypatch.delenv("PULUMI_CONFIG_PASSPHRASE_FILE", raising=False)


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
    return dummy_infrastructure_configuration()


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
            - id:                       primary
              domain:                   test.example.com
              description:              Primary domain
              google_site_verification: primary_verification
              dkim_v1:
                - selector:   test1
                  key_type:   rsa
                  public_key: test1_public_key

                - selector:   test2
                  key_type:   ed25519
                  public_key: test2_public_key

            - id:                       personal
              domain:                   personal.test.example.com
              description:              Personal domain
              google_site_verification: personal_verification

        aws_organization:
            management_account:
                account_id: "000000000777"

            infrastructure_manager_role:      arn:aws:iam::000000000777:role/MyInfraRole
            organization_account_access_role: MyRole

            organization_id:       o-ooooooooid
            root_ou_id:            r-xxou
            preferred_region:      us-west-1
            personal_iam_user:     john.doe
            sso_user:              john.doe@personal.test.example.com
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
