"""
projects.homelab.traefik.project
================================

This module contains the project definition for the homelab.traefik project.
"""

from pathlib import Path
from typing import Any

import pulumi_aws as aws
import pulumi_kubernetes as k8s
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

from ...dns import DNSZonesProject
from ..kubernetes import (
    helm_release,
    HomelabKubernetesPersistentVolume,
    HomelabKubernetesPersistentVolumeArgs,
    namespace,
    uid_gid,
)
from .config import TraefikConfiguration as traefik_config


class HomelabTraefikProject(InfrastructureProject):
    """
    Project that installs Traefik on the homelab Kubernetes cluster.
    """

    name = "homelab.traefik"
    service_name = "traefik"

    chart_oci_uri = "oci://ghcr.io/traefik/helm/traefik"
    chart_version = "41.0.0"
    chart_sha256 = "c7425a28bdc731dcb59a61cf85349463a235bf76c3c5f9f42ca8f6e2dbc62f72"

    data_path = Path("/data")

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
        homelab_domain = self.dctx.config.domains["homelab"]
        homelab_domain_fqdn = homelab_domain.domain_for(self.dctx.target)
        self.homelab_zone, self.dns_provider = DNSZonesProject.lookup_zone(
            self.dctx,
            homelab_domain_fqdn,
        )
        k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.default_ropts = ResourceOptions(provider=k8s_provider)
        self.ns_name, self.ns = namespace(
            "namespace",
            self.dctx.target.environment,
            self.service_name,
            opts=self.default_ropts,
        )
        self._configure_dns_update_credentials()
        self._configure_kubernetes_volume()

        helm_release(
            "traefik",
            oci_uri=self.chart_oci_uri,
            version=self.chart_version,
            sha256=self.chart_sha256,
            namespace=self.ns_name,
            values=self._traefik_chart_values(),
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
                Statement(
                    sid="AllowDNSZoneRead",
                    effect="Allow",
                    actions=["route53:ListResourceRecordSets"],
                    resources=[
                        self.homelab_zone.arn,
                    ],
                ),
                Statement(
                    sid="AllowDNSGetChange",
                    effect="Allow",
                    actions=["route53:GetChange"],
                    resources=["*"],
                ),
            ],
            opts=InvokeOptions(provider=self.dns_provider),
        )
        policy = aws.iam.Policy(
            "acme_dns_update",
            name="HomelabDNSChallengeAccess",
            path="/homelab/",
            description="Grants access to perform ACME DNS challenges in the homelab zone.",
            policy=dns_update_policy.json,
            opts=dns_ropts,
        )
        self.traefik_user = aws.iam.User(
            "acme_dns_update",
            name="traefik",
            path="/homelab/",
            opts=dns_ropts,
        )
        self.traefik_user_key = aws.iam.AccessKey(
            "acme_dns_update",
            user=self.traefik_user.name,
            opts=dns_ropts,
        )
        self.traefik_dns_update_secret = k8s.core.v1.Secret(
            "acme_dns_update_secret",
            metadata=k8s.meta.v1.ObjectMetaArgs(
                namespace=self.ns_name,
                name="acme-dns-update",
            ),
            string_data={
                "aws_access_key_id": self.traefik_user_key.id,
                "aws_secret_access_key": self.traefik_user_key.secret,
            },
            opts=self.default_ropts,
        )
        aws.iam.UserPolicyAttachment(
            "acme_dns_update",
            user=self.traefik_user.name,
            policy_arn=policy.arn,
            opts=dns_ropts,
        )

    def _configure_kubernetes_volume(self) -> None:
        """
        Configures the Kubernetes volume for Traefik.
        """
        self.data_volume = HomelabKubernetesPersistentVolume(
            "volume",
            args=HomelabKubernetesPersistentVolumeArgs(
                name="data",
                namespace=self.ns_name,
                backing_volume="data0",
                storage="128Mi",
                access_modes=["ReadWriteOnce"],
                user=uid_gid(self.dctx.target.environment, "traefik"),
                group=uid_gid(self.dctx.target.environment, "traefik"),
                mode="0700",
            ),
            dctx=self.dctx,
            opts=self.default_ropts,
        )

    def _traefik_chart_values(self) -> dict[str, Any]:
        """
        Returns the chart values for Traefik.
        """
        homelab_domain = self.dctx.config.domains["homelab"]
        homelab_domain_fqdn = homelab_domain.domain_for(self.dctx.target)

        cert_resolver_defn = {
            "acme": {
                "email": f"acme@{homelab_domain_fqdn}",
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
        }

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
                traefik_config.cert_resolver: cert_resolver_defn,
                "gcp": cert_resolver_defn,
            },
            "env": [
                {
                    "name": "AWS_ACCESS_KEY_ID",
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": self.traefik_dns_update_secret.metadata["name"],
                            "key": "aws_access_key_id",
                        }
                    },
                },
                {
                    "name": "AWS_SECRET_ACCESS_KEY",
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": self.traefik_dns_update_secret.metadata["name"],
                            "key": "aws_secret_access_key",
                        }
                    },
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
                "existingClaim": self.data_volume.pvc.name,
            },
            "podSecurityContext": {
                "runAsUser": uid_gid(self.dctx.target.environment, "traefik"),
                "runAsGroup": uid_gid(self.dctx.target.environment, "traefik"),
            },
            "ports": {
                traefik_config.insecure_entrypoint: {
                    "port": 8888,
                    "exposedPort": traefik_config.http_port,
                    "http": {
                        "redirections": {
                            "entryPoint": {
                                "to": traefik_config.secure_entrypoint,
                                "scheme": "https",
                                "permanent": True,
                            },
                        },
                    },
                },
                traefik_config.secure_entrypoint: {
                    "port": 8443,
                    "exposedPort": traefik_config.https_port,
                    "asDefault": True,
                    "http": {
                        "tls": {
                            "enabled": True,
                            "certResolver": traefik_config.cert_resolver,
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
