"""
infralib/testing/config -- Dummy Infrastructure Configuration
=============================================================

This module contains the dummy configuration that renders and tests use. Rendered
output is committed to the repository, so these values must never be real.
"""

from ipaddress import IPv4Address, IPv4Network

from ..config import InfrastructureConfiguration
from ..config.aws import AWSAccount, AWSOrganization
from ..config.domain import Domain, DKIMv1
from ..config.gcp import GCPOrganization
from ..config.homelab import (
    Homelab,
    HomelabDHCP,
    HomelabDHCPAssignment,
    HomelabDHCPRange,
    HomelabDNSRecord,
    HomelabNetwork,
    HomelabNetworking,
    HomelabNetworks,
    HomelabPortForward,
    HomelabPPPoE,
    HomelabRouter,
    HomelabRouterAdmin,
    HomelabSNMP,
    HomelabSwitch,
    HomelabSwitchPort,
)
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
        "wedding": Domain(
            id="wedding",
            domain="wedding.test.example.com",
            description="Wedding domain",
            dkim_v1=[],
            google_site_verification="wedding_verification",
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
        network=HomelabNetworking(
            upstream_dns=[IPv4Address("192.0.2.53"), IPv4Address("198.51.100.53")],
            networks=HomelabNetworks(
                trusted=HomelabNetwork(
                    name="trusted",
                    ipv4_network=IPv4Network("10.0.12.0/23"),
                    dhcp=HomelabDHCP(
                        range=HomelabDHCPRange(
                            start=IPv4Address("10.0.12.10"),
                            end=IPv4Address("10.0.12.250"),
                        ),
                        assignments=[
                            HomelabDHCPAssignment(
                                name="test-host",
                                mac="00:00:5e:00:53:01",
                                ip=IPv4Address("10.0.12.5"),
                                dns=["test-host.lan"],
                            ),
                        ],
                    ),
                ),
                wireguard_trusted=HomelabNetwork(
                    "wireguard_trusted", IPv4Network("10.0.15.0/24")
                ),
                modem=HomelabNetwork("modem", IPv4Network("10.0.1.0/24")),
                kube_cluster=HomelabNetwork(
                    "kube_cluster", IPv4Network("10.0.16.0/22")
                ),
                kube_service=HomelabNetwork("kube_service", IPv4Network("10.0.8.0/22")),
                infra=HomelabNetwork(
                    "infra",
                    IPv4Network("10.0.2.0/24"),
                    dhcp=HomelabDHCP(
                        assignments=[
                            HomelabDHCPAssignment(
                                name="kserv",
                                mac="00:00:5e:00:53:02",
                                ip=IPv4Address("10.0.2.5"),
                            ),
                        ],
                    ),
                ),
                mgmt=HomelabNetwork("mgmt", IPv4Network("10.0.4.0/22")),
                mgmt_backup=HomelabNetwork("mgmt_backup", IPv4Network("10.0.3.0/24")),
                lockdown=HomelabNetwork(
                    "lockdown", IPv4Network("10.0.21.0/24"), vlan_id=21
                ),
                net_infra=HomelabNetwork(
                    "net_infra", IPv4Network("10.0.20.0/24"), vlan_id=20
                ),
                untrusted=HomelabNetwork(
                    "untrusted", IPv4Network("10.0.14.0/24"), vlan_id=14
                ),
            ),
            switches=[
                HomelabSwitch(
                    name="test-switch",
                    address=IPv4Address("10.0.4.2"),
                    ports=[
                        HomelabSwitchPort(
                            port="0/1",
                            untagged="trusted",
                            tagged=["untrusted", "net_infra"],
                            description="router uplink",
                        ),
                        HomelabSwitchPort(port="0/2", untagged="untrusted"),
                    ],
                ),
            ],
            dns_records=[
                HomelabDNSRecord(
                    name="test-record",
                    ip=IPv4Address("10.0.2.10"),
                    dns=["test-record.lan"],
                ),
            ],
            port_forwards=[
                HomelabPortForward(
                    description="https",
                    src_port=443,
                    dest_ip=IPv4Address("10.0.2.10"),
                    dest_port=443,
                    protocol="tcp",
                ),
            ],
            router=HomelabRouter(
                admin=HomelabRouterAdmin(
                    username="test-admin",
                    full_name="Test Admin",
                    encrypted_password="$5$testsalt$" + "a" * 43,
                    pubkey="ssh-ed25519 AAAAtest",
                ),
                pppoe=HomelabPPPoE(
                    username="test-pppoe", password="test-pppoe-password"
                ),
            ),
            snmp=HomelabSNMP(community="test-community"),
        ),
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
