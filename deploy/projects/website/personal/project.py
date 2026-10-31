"""
projects.website.personal.project
=================================

This module contains the InfrastructureProject for the personal website.
"""

from pulumi import export, ResourceOptions

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ...aws.accounts import AWSAccountsProject
from ...dns import DNSZonesProject
from ...dns.route53 import route53_alias_record

from .cert import provision_certificate
from .cloudfront import provision_distribution
from .redirect import provision_redirect_distribution
from .s3 import (
    provision_assets_bucket,
    provision_site_bucket,
    provision_site_bucket_policy,
)


class WebsitePersonalProject(InfrastructureProject):
    """
    Project that hosts the personal website: a private S3 bucket served through
    CloudFront at the apex and "www" hosts of the personal domain. In production,
    the apex of the legacy personal domain redirects to the apex of the personal
    domain.

    NOTE: Site content is not managed here. Publish it to the site_bucket output
    with `aws s3 sync`, and upload anything in the assets_bucket output by hand.
    """

    name = "website.personal"
    domain_id = "personal"
    legacy_domain_id = "personal_legacy"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [
            AWSAccountsProject.stack(target),
            # dns.zones/prod is the single source for zone lookups in every
            # environment.
            DNSZonesProject.stack(DeploymentTarget(Environment.PROD, None)),
        ]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(e, None) for e in [Environment.DEV, Environment.PROD]]

    def pulumi_program(self) -> None:
        account, provider = AWSAccountsProject.lookup_account(
            self.dctx,
            "personal-website",
            self.dctx.target.environment,
        )
        aws_opts = ResourceOptions(provider=provider)

        apex = self.dctx.config.domains[self.domain_id].domain_for(self.dctx.target)
        www = f"www.{apex}"

        site_bucket, site_bucket_access_block = provision_site_bucket(
            self.dctx, account.id, aws_opts
        )
        assets_bucket = provision_assets_bucket(self.dctx, account.id, aws_opts)
        certificate_arn = provision_certificate(
            self.dctx, "site", {"apex": apex, "www": www}, aws_opts
        )
        distribution = provision_distribution(
            self.dctx,
            aliases=[apex, www],
            bucket=site_bucket,
            certificate_arn=certificate_arn,
            aws_opts=aws_opts,
        )
        provision_site_bucket_policy(
            bucket=site_bucket,
            access_block=site_bucket_access_block,
            distribution=distribution,
            aws_opts=aws_opts,
        )

        # These are alias records because the apex of the personal domain also
        # holds the TXT and MX records from dns.core, and a CNAME cannot coexist
        # with them.
        for host, name in [("apex", "."), ("www", "www")]:
            for record_type in ["A", "AAAA"]:
                route53_alias_record(
                    f"{host}.{record_type.lower()}",
                    dctx=self.dctx,
                    domain_id=self.domain_id,
                    name=name,
                    type=record_type,
                    alias_name=distribution.domain_name,
                    alias_zone_id=distribution.hosted_zone_id,
                )

        # dns.zones only provisions a zone for the legacy domain in production.
        if self.dctx.target.environment == Environment.PROD:
            self._configure_legacy_redirect(apex, aws_opts)

        export("assets_bucket", assets_bucket.bucket)
        export("distribution_id", distribution.id)
        export("site_bucket", site_bucket.bucket)
        export("site_url", f"https://{apex}")

    def _configure_legacy_redirect(
        self, target_host: str, aws_opts: ResourceOptions
    ) -> None:
        """
        Configures the apex of the legacy domain to redirect to the given host.

        NOTE: The certificate only validates once the legacy domain's registrar
        delegates to the zone from dns.zones.
        """
        legacy_apex = self.dctx.config.domains[self.legacy_domain_id].domain_for(
            self.dctx.target
        )
        certificate_arn = provision_certificate(
            self.dctx, "legacy_redirect", {"legacy_apex": legacy_apex}, aws_opts
        )
        distribution = provision_redirect_distribution(
            self.dctx,
            alias=legacy_apex,
            target_host=target_host,
            certificate_arn=certificate_arn,
            aws_opts=aws_opts,
        )

        # As with the personal domain, dns.core also manages TXT and MX records
        # at this apex, which a CNAME cannot coexist with.
        for record_type in ["A", "AAAA"]:
            route53_alias_record(
                f"legacy_apex.{record_type.lower()}",
                dctx=self.dctx,
                domain_id=self.legacy_domain_id,
                name=".",
                type=record_type,
                alias_name=distribution.domain_name,
                alias_zone_id=distribution.hosted_zone_id,
            )

        export("legacy_redirect_distribution_id", distribution.id)
