"""
projects.website.wedding.project
================================

This module contains the InfrastructureProject for the wedding website.
"""

from pulumi import export, Output, ResourceOptions
from pulumi_aws.s3 import (
    BucketCorsConfiguration,
    BucketCorsConfigurationCorsRuleArgs as CorsRule,
)

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from ...aws.accounts import AWSAccountsProject
from ...dns import DNSZonesProject
from ...dns.route53 import route53_alias_record

from ..cert import provision_certificate
from ..redirect import provision_redirect_distribution
from ..s3 import private_bucket, provision_site_bucket_policy

from .cloudfront import provision_distribution


class WebsiteWeddingProject(InfrastructureProject):
    """
    Project that hosts the wedding website: a private S3 bucket served through
    CloudFront under the production primary domain: at the "wedding" host in
    production, and at "<environment>.wedding" elsewhere. The apex and "www" hosts
    of the wedding domain permanently redirect there.

    NOTE: Site content is not managed here. Publish it to the site_bucket output
    with `aws s3 sync`.

    NOTE: The redirect's certificate only validates once the wedding domain's
    registrar delegates to the zone from dns.zones.
    """

    name = "website.wedding"
    primary_domain_id = "primary"
    site_host_label = "wedding"
    wedding_domain_id = "wedding"

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
        environment = self.dctx.target.environment
        account, provider = AWSAccountsProject.lookup_account(
            self.dctx, "wedding-website", environment
        )
        aws_opts = ResourceOptions(provider=provider)

        # Every environment's site lives under the production primary domain, so
        # the environment goes in the label rather than the domain.
        prod = DeploymentTarget(Environment.PROD, None)
        primary_domain = self.dctx.config.domains[self.primary_domain_id]
        env_host = primary_domain.host_for(self.dctx.target)
        site_label = (
            f"{env_host}.{self.site_host_label}" if env_host else self.site_host_label
        )
        site_host = f"{site_label}.{primary_domain.domain_for(prod)}"

        # The contents can be republished at any time, so the bucket is not
        # protected.
        site_bucket, access_block = private_bucket(
            "site_bucket",
            f"{environment}-wedding-website-{account.id}",
            aws_opts,
        )
        BucketCorsConfiguration(
            "site_bucket",
            bucket=site_bucket.bucket,
            cors_rules=[CorsRule(allowed_methods=["GET"], allowed_origins=["*"])],
            opts=aws_opts,
        )
        certificate_arn = provision_certificate(
            self.dctx, "site", {"site": site_host}, aws_opts
        )
        distribution = provision_distribution(
            self.dctx,
            aliases=[site_host],
            bucket=site_bucket,
            certificate_arn=certificate_arn,
            aws_opts=aws_opts,
        )
        provision_site_bucket_policy(
            bucket=site_bucket,
            access_block=access_block,
            distribution=distribution,
            aws_opts=aws_opts,
        )
        for record_type in ["A", "AAAA"]:
            route53_alias_record(
                f"site.{record_type.lower()}",
                dctx=self.dctx,
                domain_id=self.primary_domain_id,
                name=site_label,
                type=record_type,
                alias_name=distribution.domain_name,
                alias_zone_id=distribution.hosted_zone_id,
                target=prod,
            )

        redirect_distribution_id = self._configure_redirect(site_host, aws_opts)

        export("distribution_id", distribution.id)
        export("redirect_distribution_id", redirect_distribution_id)
        export("site_bucket", site_bucket.bucket)
        export("site_url", f"https://{site_host}")

    def _configure_redirect(
        self, target_host: str, aws_opts: ResourceOptions
    ) -> Output[str]:
        """
        Configures the apex and "www" hosts of the wedding domain to redirect to
        the given host, and returns the ID of the redirecting distribution.
        """
        apex = self.dctx.config.domains[self.wedding_domain_id].domain_for(
            self.dctx.target
        )
        www = f"www.{apex}"
        certificate_arn = provision_certificate(
            self.dctx, "redirect", {"apex": apex, "www": www}, aws_opts
        )
        distribution = provision_redirect_distribution(
            "redirect",
            f"{self.dctx.target.environment}-wedding-website-redirect",
            aliases=[apex, www],
            target_host=target_host,
            certificate_arn=certificate_arn,
            aws_opts=aws_opts,
        )

        # These are alias records because dns.core also manages TXT and MX
        # records at the production apex, which a CNAME cannot coexist with.
        for host, name in [("apex", "."), ("www", "www")]:
            for record_type in ["A", "AAAA"]:
                route53_alias_record(
                    f"redirect.{host}.{record_type.lower()}",
                    dctx=self.dctx,
                    domain_id=self.wedding_domain_id,
                    name=name,
                    type=record_type,
                    alias_name=distribution.domain_name,
                    alias_zone_id=distribution.hosted_zone_id,
                )

        return distribution.id
