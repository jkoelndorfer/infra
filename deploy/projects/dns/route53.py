"""
projects.dns.route53
====================

This module contains Route 53 helpers.
"""

from typing import Sequence, Union

from pulumi import Input, ResourceOptions
import pulumi_aws as aws

from infralib import DeploymentContext, DeploymentTarget
from infralib.config.domain import DomainID

from .zones import DNSZonesProject


def route53_record(
    resource_name: str,
    dctx: DeploymentContext,
    domain_id: DomainID,
    name: str,
    type: Input[Union[str, aws.route53.RecordType]],
    ttl: Input[int],
    records: Input[Sequence[Input[str]]],
    target: DeploymentTarget | None = None,
    opts: ResourceOptions | None = None,
) -> aws.route53.Record:
    """
    Provisions a Route 53 DNS record.

    The correct zone and provider are retrieved from the dns.zones project.
    """
    domain = dctx.config.domains[domain_id]
    if target is None:
        target = dctx.target

    if name.strip(".") == "":
        fqdn = domain.domain_for(target)
    else:
        fqdn = f"{name}.{domain.domain_for(target)}"

    zone, provider = DNSZonesProject.lookup_zone(dctx, fqdn)

    implicit_opts = ResourceOptions(provider=provider)
    if opts is not None:
        opts = opts.merge(implicit_opts)
    else:
        opts = implicit_opts

    return aws.route53.Record(
        resource_name,
        name=fqdn,
        type=type,
        ttl=ttl,
        records=records,
        zone_id=zone.zone_id,
        opts=opts,
    )


def route53_alias_record(
    resource_name: str,
    dctx: DeploymentContext,
    domain_id: DomainID,
    name: str,
    type: Input[Union[str, aws.route53.RecordType]],
    alias_name: Input[str],
    alias_zone_id: Input[str],
) -> aws.route53.Record:
    """
    Provisions a Route 53 alias record.

    The correct zone and provider are retrieved from the dns.zones project.
    """
    domain = dctx.config.domains[domain_id].domain_for(dctx.target)
    fqdn = domain if name.strip(".") == "" else f"{name}.{domain}"
    zone, provider = DNSZonesProject.lookup_zone(dctx, fqdn)

    return aws.route53.Record(
        resource_name,
        name=fqdn,
        type=type,
        aliases=[
            aws.route53.RecordAliasArgs(
                name=alias_name,
                zone_id=alias_zone_id,
                evaluate_target_health=False,
            ),
        ],
        zone_id=zone.zone_id,
        opts=ResourceOptions(provider=provider),
    )
