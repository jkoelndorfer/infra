"""
tests/infralib/config/test_parser -- Configuration Parser Tests
===============================================================

This file contains code to test infralib configuration parsers.
"""

from os import PathLike

import pytest

from infralib import Environment, InfrastructureConfigurationYAMLParser
from infralib.config.notification import EmailChannel, NotificationCategory


@pytest.fixture
def yaml_parser() -> InfrastructureConfigurationYAMLParser:
    return InfrastructureConfigurationYAMLParser()


class TestInfrastructureConfigurationYAMLParser:
    """
    Container for InfrastructureConfigurationYAMLParser tests.
    """

    def test_parse_produces_expected_configuration(
        self,
        yaml_parser: InfrastructureConfigurationYAMLParser,
        test_infrastructure_yaml_configuration_path: PathLike[str],
    ) -> None:
        """
        Tests that InfrastructureConfigurationYAMLParser.parse() produces the expected configuration.
        """
        config = yaml_parser.parse(test_infrastructure_yaml_configuration_path)

        assert config.domains["primary"].domain == "test.example.com"
        assert config.domains["personal"].domain == "personal.test.example.com"

        aws_org = config.aws_organization
        assert aws_org.organization_id == "o-ooooooooid"
        assert aws_org.root_ou_id == "r-xxou"
        assert aws_org.management_account.account_id == "000000000777"
        assert (
            aws_org.member_account_email(Environment.DEV, "website")
            == "aws.dev.website@personal.test.example.com"
        )
        assert (
            aws_org.member_account_email(Environment.PROD, "backup")
            == "aws.prod.backup@personal.test.example.com"
        )
        assert aws_org.organization_account_access_role == "MyRole"
        assert aws_org.preferred_region == "us-west-1"
        assert aws_org.personal_iam_user == "john.doe"
        assert aws_org.management_account.arn == "arn:aws:account::000000000777:account"
        assert (
            aws_org.management_account.root_user_arn == "arn:aws:iam::000000000777:root"
        )
        assert (
            aws_org.infrastructure_manager_role
            == "arn:aws:iam::000000000777:role/MyInfraRole"
        )

        gcp_org = config.gcp_organization
        assert gcp_org.domain == "test.example.com"
        assert gcp_org.organization_id == "000000000888"
        assert gcp_org.billing_account_id == "000000-000000-100001"
        assert gcp_org.preferred_region == "us-west2"
        assert gcp_org.personal_iam_user == "john.doe@test.example.com"
        assert (
            gcp_org.infrastructure_manager_service_account
            == "my-infra-sa@infra-mgmt-000000000888.iam.gserviceaccount.com"
        )
        assert gcp_org.quota_project == "my-quota-project"

        nc = config.notification_channels
        nc0 = nc[0]
        nc1 = nc[1]
        assert isinstance(nc0, EmailChannel)
        assert nc0.name == "First Billing Test"
        assert nc0.email == "billing@test.example.com"
        assert nc0.category == NotificationCategory.CLOUD_BILLING

        assert isinstance(nc1, EmailChannel)
        assert nc1.name == "Second Billing Test"
        assert nc1.email == "billing.second@test.example.com"
        assert nc1.category == NotificationCategory.CLOUD_BILLING

        assert len(nc) == len(list(nc))
