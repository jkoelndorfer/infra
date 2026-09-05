"""
projects.homelab.traefik
========================

This module contains the homelab Traefik project.
"""

from pathlib import Path
from typing import Any

import pulumi_aws as aws
from pulumi_aws.iam import (
    GetPolicyDocumentStatementArgs as Statement,
    GetPolicyDocumentStatementConditionArgs as Condition,
)
from pulumi import InvokeOptions, ResourceOptions

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ..kubernetes import helm_release, namespace, uid_gid
from ...dns import DNSZonesProject


class HomelabTraefikProject(InfrastructureProject):
    """
    Project that installs Traefik on my homelab Kubernetes cluster.
    """

    name = "homelab.traefik"
    service_name = "traefik"

    cert_resolver = "homelab"

    chart_oci_uri = "oci://ghcr.io/traefik/helm/traefik"
    chart_version = "41.0.0"
    chart_sha256 = "c7425a28bdc731dcb59a61cf85349463a235bf76c3c5f9f42ca8f6e2dbc62f72"

    data_path = Path("/data")

    http_port = 80
    https_port = 443

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [
            DNSZonesProject.stack(DeploymentTarget(Environment.PROD, None)),
        ]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        # Traefik cannot be installed multiple times on one Kubernetes cluster,
        # so only prod is permitted here.
        return [
            DeploymentTarget(Environment.PROD, None),
        ]

    def pulumi_program(self) -> None:
        self.homelab_zone, self.dns_provider = DNSZonesProject.lookup_zone(
            self.dctx,
            self.dctx.config.domains["homelab"].domain,
        )
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        ns_name, ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )
        self._configure_dns_update_credentials()
        helm_release(
            "traefik",
            oci_uri=self.chart_oci_uri,
            version=self.chart_version,
            sha256=self.chart_sha256,
            namespace=ns_name,
            values={},
            opts=self.default_ropts.merge(
                ResourceOptions(import_="traefik"),
            ),
        )

    def _configure_dns_update_credentials(self) -> None:
        """
        Configures cloud provider credentials used by Traefik to update DNS
        records for ACME DNS certificate issuance.
        """
        dns_ropts = ResourceOptions(provider=self.dns_provider)
        dns_update_policy = aws.iam.get_policy_document_output(
            statements=[
                Statement(
                    sid="AllowDNSChallengeRecordManagement",
                    effect="Allow",
                    actions=["route53:ChangeResourceRecordSets"],
                    resources=[
                        self.homelab_zone.arn,
                    ],
                    conditions=[
                        Condition(
                            variable="route53:ChangeResourceRecordSetsNormalizedRecordNames",
                            test="ForAllValues:StringLike",
                            values=[
                                f"_acme-challenge.{self.homelab_zone.name}",
                                f"_acme-challenge.*.{self.homelab_zone.name}",
                            ],
                        ),
                        Condition(
                            variable="route53:ChangeResourceRecordSetsRecordTypes",
                            test="ForAllValues:StringEquals",
                            values=[
                                "CNAME",
                                "TXT",
                            ],
                        ),
                    ],
                ),
            ],
            opts=InvokeOptions(provider=self.dns_provider),
        )
        aws.iam.Policy(
            "acme_dns_update",
            name="HomelabDNSChallengeAccess",
            path="/homelab",
            description="Grants access to perform ACME DNS challenges in the homelab zone.",
            policy=dns_update_policy.json,
            opts=dns_ropts,
        )
        self.traefik_user = aws.iam.User(
            "acme_dns_update",
            name="traefik",
            path="/homelab",
            opts=dns_ropts,
        )
        self.traefik_user_key = aws.iam.AccessKey(
            "acme_dns_update",
            user=self.traefik_user.name,
            opts=dns_ropts,
        )

    def _traefik_chart_values(self) -> dict[str, Any]:
        """
        Returns the chart values for Traefik.
        """
        return {
            "api": {
                "dashboard": True,
                "insecure": False,
            },
            "metrics": {
                "prometheus": {
                    "enabled": False,
                },
            },
            "certificatesResolvers": {
                self.cert_resolver: {
                    "acme": {
                        "email": f"acme@{self.dctx.config.domains['personal'].domain}",
                        "storage": str(self.data_path / "acme.json"),
                        # Traefik uses Lego [1, 2] for ACME. Traefik refers us to
                        # Lego's list of DNS challenge providers [3].
                        #
                        # [1]: https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/#dnschallenge
                        # [2]: https://go-acme.github.io/lego/
                        # [3]: https://go-acme.github.io/lego/dns/index.html
                        "dnsChallenge": {
                            # https://go-acme.github.io/lego/dns/route53/
                            #
                            # Environment variables are set in env below.
                            "provider": "route53",
                            "resolvers": [
                                "8.8.8.8",
                                "8.8.4.4",
                            ],
                        },
                    },
                },
            },
            "env": [
                {
                    "name": "AWS_ACCESS_KEY_ID",
                    "value": self.traefik_user_key.id,
                },
                {
                    "name": "AWS_SECRET_ACCESS_KEY",
                    "value": self.traefik_user_key.secret,
                },
                {
                    "name": "AWS_HOSTED_ZONE_ID",
                    "value": self.homelab_zone.zone_id,
                },
                {
                    "name": "AWS_REGION",
                    "value": self.dctx.config.aws_organization.preferred_region,
                },
            ],
            "persistence": {
                "enabled": True,
                "name": "data",
                "path": str(self.data_path),
                # TODO: Implement this.
                "existingClaim": "TODO: module.cert_volume.pvc.name",
            },
            "podSecurityContext": {
                "runAsUser": uid_gid(self.dctx.target.environment, "traefik"),
                "runAsGroup": uid_gid(self.dctx.target.environment, "traefik"),
            },
            "ports": {
                "web": {
                    "port": 8888,
                    "exposedPort": self.http_port,
                    "http": {
                        "redirections": {
                            "entryPoint": {
                                "to": "websecure",
                                "scheme": "https",
                                "permanent": True,
                            },
                        },
                    },
                },
                "websecure": {
                    "port": 8443,
                    "exposedPort": self.https_port,
                    "asDefault": True,
                    "http": {
                        "tls": {
                            "enabled": True,
                            "certResolver": self.cert_resolver,
                        },
                    },
                },
            },
            "tlsOptions": {
                "default": {
                    "sniStrict": True,
                },
            },
        }
