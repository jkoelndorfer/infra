"""
projects.website.cert
=====================

This module contains TLS certificates for websites.
"""

from pulumi import Output, ResourceOptions
import pulumi_aws as aws

from infralib import DeploymentContext

from ..dns import DNSZonesProject

# CloudFront only accepts ACM certificates from this region [1].
#
# [1]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html
CERTIFICATE_REGION = "us-east-1"


def provision_certificate(
    dctx: DeploymentContext,
    resource_name: str,
    hosts: dict[str, str],
    aws_opts: ResourceOptions,
) -> Output[str]:
    """
    Provisions a certificate covering the given hosts, validated through DNS.

    Hosts map a label, which names the host's validation record, to a domain
    name. The first host is the certificate's primary domain name.

    Returns the certificate's ARN, which resolves only once validation has
    completed.
    """
    domains = list(hosts.values())
    certificate = aws.acm.Certificate(
        resource_name,
        domain_name=domains[0],
        subject_alternative_names=domains[1:] or None,
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

    records = [validation_record(host, domain) for host, domain in hosts.items()]
    validation = aws.acm.CertificateValidation(
        resource_name,
        certificate_arn=certificate.arn,
        validation_record_fqdns=[r.fqdn for r in records],
        region=CERTIFICATE_REGION,
        opts=aws_opts,
    )
    return validation.certificate_arn
