"""
projects.dns.core
=================

This module contains core DNS configuration. Things like apex domain
TXT records must be managed centrally, due to living inside one record.
This project does that.

Additionally, email configuration is handled here.
"""

from dataclasses import dataclass
from typing import ClassVar, Literal

import pulumi_aws as aws

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)
from infralib.config.domain import Domain

from .route53 import route53_record
from .zones import DNSZonesProject


@dataclass
class SMTP2GOConfiguration:
    return_value: ClassVar[str] = "return.smtp2go.net"
    dkim_value: ClassVar[str] = "dkim.smtp2go.net"

    # The SPF configuration for SMTP2GO. This isn't required in most circumstances
    # for SMTP2GO since it uses Variable Envelope Return Path (VERP). We configure
    # it anyway, for completeness.
    #
    # See https://support.smtp2go.com/hc/en-gb/articles/16994667206937-Maintaining-the-Return-path.
    spf: ClassVar[str] = "include:spf.smtp2go.com"

    return_host: str
    dkim_selector: str


class DNSCoreProject(InfrastructureProject):
    """
    Project that configures core infrastructure DNS records, like Google
    site verification and email (MX, SPF, and DMARC).
    """

    name = "dns.core"

    # The SPF configuration for Google Workspace.
    #
    # See https://knowledge.workspace.google.com/admin/security/set-up-spf.
    google_spf = "include:_spf.google.com"

    # SMTP2GO Hostnames for the return and DKIM records. These
    # appear to be domain-specific.
    #
    # See https://app-us.smtp2go.com/sending/verified_senders.
    smtp2go = {
        "homelab": SMTP2GOConfiguration(
            return_host="em911349",
            dkim_selector="s911349",
        )
    }

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [DNSZonesProject.stack(DeploymentTarget(Environment.PROD, None))]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(Environment.PROD, None)]

    def pulumi_program(self) -> None:
        for domain in self.dctx.config.domains.values():
            if domain.id == "homelab":
                continue

            self._configure_google_hosted_domain(domain)
            self._configure_domain_dkim1(domain)
            self._configure_domain_dmarc1(
                domain=domain,
                p="reject",
                pct=100,
                adkim=None,
                aspf=None,
                fo=["1"],
                ri=None,
                rua=[f"mailto:dmarc@{domain.domain_for(self.dctx.target)}"],
                ruf=None,
                sp=None,
            )

        homelab_domain = self.dctx.config.domains["homelab"]
        self._configure_smtp2go_domain(homelab_domain)

    def _configure_domain_dkim1(
        self,
        domain: Domain,
    ) -> None:
        """
        Configures DKIM version 1 records for the given domain.
        """
        for dkim in domain.dkim_v1:
            dkim_record = {
                "v": dkim.version,
                "k": dkim.key_type,
                "p": dkim.public_key,
            }
            route53_record(
                f"domain.{domain.id}.dkim_v1.{dkim.selector}",
                dctx=self.dctx,
                name=f"{dkim.selector}._domainkey",
                domain_id=domain.id,
                type=aws.route53.RecordType.TXT,
                ttl=600,
                records=[
                    "; ".join([f"{k}={v}" for k, v in dkim_record.items()]),
                ],
            )

    def _configure_domain_dmarc1(
        self,
        domain: Domain,
        p: Literal["none", "quarantine", "reject"],
        pct: int,
        adkim: Literal[None, "s", "r"],
        aspf: Literal[None, "s", "r"],
        fo: list[Literal["0", "1", "d", "s"]],
        ri: int | None,
        rua: list[str] | None,
        ruf: list[str] | None,
        sp: Literal[None, "none", "quarantine", "reject"],
    ) -> None:
        """
        Configures DMARC version 1 records for the given domain.

        See https://mxtoolbox.com/dmarc/details/what-is-a-dmarc-record
        """
        if not (0 <= pct <= 100):
            raise ValueError("pct must be between 0 and 100, inclusive")

        if ri is not None and ri < 86400:
            # See https://mxtoolbox.com/dmarc/details/dmarc-tags/dmarc-report-interval
            raise ValueError("ri must be one day (86400 seconds) or greater")

        dmarc_values = {
            "v": "DMARC1",
            "p": p,
            "pct": pct,
            "adkim": adkim,
            "aspf": aspf,
            "fo": ":".join(fo),
            "ri": ri,
            "rua": ",".join(rua) if rua else None,
            "ruf": ",".join(ruf) if ruf else None,
            "sp": sp,
        }
        dmarc_record = ";".join([f"{k}={v}" for k, v in dmarc_values.items() if v])

        route53_record(
            f"domain.{domain.id}.dmarc",
            dctx=self.dctx,
            domain_id=domain.id,
            name="_dmarc",
            type=aws.route53.RecordType.TXT,
            ttl=600,
            records=[dmarc_record],
        )

    def _configure_google_hosted_domain(self, domain: Domain) -> None:
        """
        Configures a domain powered by Google Workspace.
        """
        records = [
            f"v=spf1 {self.google_spf} ~all",
        ]

        if domain.google_site_verification is not None:
            records.append(
                f"google-site-verification={domain.google_site_verification}"
            )

        route53_record(
            f"domain.{domain.id}.apex_txt",
            dctx=self.dctx,
            domain_id=domain.id,
            name=".",
            type=aws.route53.RecordType.TXT,
            ttl=600,
            records=records,
        )

        # See https://knowledge.workspace.google.com/admin/domains/set-up-mx-records-for-google-workspace
        route53_record(
            f"domain.{domain.id}.mx",
            dctx=self.dctx,
            domain_id=domain.id,
            name=".",
            type=aws.route53.RecordType.MX,
            ttl=600,
            records=["1 smtp.google.com"],
        )

    def _configure_smtp2go_domain(self, domain: Domain) -> None:
        smtp2go_config = self.smtp2go[domain.id]

        route53_record(
            f"domain.{domain.id}.mx",
            dctx=self.dctx,
            domain_id=domain.id,
            name=".",
            type=aws.route53.RecordType.MX,
            ttl=600,
            records=["1 smtp.google.com"],
        )

        route53_record(
            f"domain.{domain.id}.smtp2go_spf",
            dctx=self.dctx,
            domain_id=domain.id,
            name=".",
            type=aws.route53.RecordType.TXT,
            ttl=600,
            records=[f"v=spf1 {smtp2go_config.spf} {self.google_spf} ~all"],
        )

        route53_record(
            f"domain.{domain.id}.smtp2go_return",
            dctx=self.dctx,
            domain_id=domain.id,
            name=smtp2go_config.return_host,
            type=aws.route53.RecordType.CNAME,
            ttl=600,
            records=[smtp2go_config.return_value],
        )

        route53_record(
            f"domain.{domain.id}.smtp2go_dkim",
            dctx=self.dctx,
            domain_id=domain.id,
            name=f"{smtp2go_config.dkim_selector}._domainkey",
            type=aws.route53.RecordType.CNAME,
            ttl=600,
            records=[smtp2go_config.dkim_value],
        )
