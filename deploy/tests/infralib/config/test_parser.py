"""
tests/infralib/config/test_parser -- Configuration Parser Tests
===============================================================

This file contains code to test infralib configuration parsers.
"""

from ipaddress import IPv4Address
from os import PathLike

import pytest

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureConfigurationYAMLParser,
)
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
        prod = DeploymentTarget(Environment.PROD, None)

        primary_domain = config.domains["primary"]
        assert primary_domain.domain_for(prod) == "test.example.com"
        assert primary_domain.google_site_verification == "primary_verification"
        assert len(primary_domain.dkim_v1) == 2

        assert primary_domain.dkim_v1[0].selector == "test1"
        assert primary_domain.dkim_v1[0].key_type == "rsa"
        assert primary_domain.dkim_v1[0].public_key == "test1_public_key"

        assert primary_domain.dkim_v1[1].selector == "test2"
        assert primary_domain.dkim_v1[1].key_type == "ed25519"
        assert primary_domain.dkim_v1[1].public_key == "test2_public_key"

        personal_domain = config.domains["personal"]
        assert personal_domain.domain_for(prod) == "personal.test.example.com"
        assert personal_domain.google_site_verification == "personal_verification"

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
        assert aws_org.sso_user == "john.doe@personal.test.example.com"
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

        homelab = config.homelab
        assert homelab.kubernetes_context == "k8stest"
        assert str(homelab.network.upstream_dns[1]) == "198.51.100.53"
        trusted = homelab.network.networks.trusted
        assert trusted.name == "trusted"
        assert str(trusted.ipv4_network) == "10.0.12.0/23"
        assert trusted.vlan_id == 12
        assert trusted.dhcp is not None
        assert trusted.dhcp.range is not None
        assert str(trusted.dhcp.range.end) == "10.0.12.250"
        assert trusted.dhcp.assignments[0].mac == "00:00:5e:00:53:01"
        assert str(homelab.network.networks.mgmt.ipv4_network) == "10.0.4.0/22"
        assert str(homelab.network.networks.mgmt_backup.ipv4_network) == "10.0.3.0/24"
        assert homelab.network.networks.net_infra.vlan_id == 20
        assert homelab.network.networks.lockdown.vlan_id == 21
        assert str(homelab.network.networks.untrusted.ipv4_network) == "10.0.14.0/24"
        assert (
            str(homelab.network.networks.wireguard_trusted.ipv4_network)
            == "10.0.15.0/24"
        )
        assert str(homelab.network.networks.kube_cluster.ipv4_network) == "10.0.16.0/22"
        assert str(homelab.network.networks.kube_service.ipv4_network) == "10.0.8.0/22"
        switch = homelab.network.switches[0]
        assert switch.name == "test-switch"
        assert switch.ports[0].port == "0/1"
        assert switch.ports[0].untagged == "trusted"
        assert switch.ports[0].tagged == ["untrusted", "net_infra"]
        assert homelab.network.dns_records[0].dns == ["test-record.lan"]
        assert homelab.network.port_forwards[0].dest_port == 443
        assert homelab.network.router.admin.pubkey_key == "AAAAtest"
        assert homelab.network.router.pppoe.password == "test-pppoe-password"
        assert homelab.network.snmp.community == "test-community"
        assert homelab.network.switches[0].address == IPv4Address("10.0.4.2")

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
