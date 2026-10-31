"""
projects.website.personal.cert
==============================

This module contains the TLS certificate for the personal website.
"""

from pulumi import Output, ResourceOptions
import pulumi_aws as aws

from infralib import DeploymentContext

from ...dns import DNSZonesProject

# CloudFront only accepts ACM certificates from this region [1].
#
# [1]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html
CERTIFICATE_REGION = "us-east-1"


def provision_certificate(
    dctx: DeploymentContext,
    apex: str,
    www: str,
    aws_opts: ResourceOptions,
) -> Output[str]:
    """
    Provisions a certificate covering the given hosts, validated through DNS.

    Returns the certificate's ARN, which resolves only once validation has
    completed.
    """
    certificate = aws.acm.Certificate(
        "site",
        domain_name=apex,
        subject_alternative_names=[www],
        validation_method="DNS",
        region=CERTIFICATE_REGION,
        opts=aws_opts,
    )

    def validation_record(host: str, domain: str) -> aws.route53.Record:
        # The validation options are looked up by domain because the provider
        # does not guarantee their order.
        option = certificate.domain_validation_options.apply(
            lambda options: next(o for o in options if o.domain_name == domain)
        )
        zone, provider = DNSZonesProject.lookup_zone(dctx, domain)
        return aws.route53.Record(
            f"cert_validation.{host}",
            zone_id=zone.zone_id,
            name=option.resource_record_name,
            type=option.resource_record_type,
            records=[option.resource_record_value],
            ttl=300,
            opts=ResourceOptions(provider=provider),
        )

    records = [validation_record("apex", apex), validation_record("www", www)]
    validation = aws.acm.CertificateValidation(
        "site",
        certificate_arn=certificate.arn,
        validation_record_fqdns=[r.fqdn for r in records],
        region=CERTIFICATE_REGION,
        opts=aws_opts,
    )
    return validation.certificate_arn
