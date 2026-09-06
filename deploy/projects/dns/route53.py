"""
projects.dns.route53
====================

This module contains Route 53 helpers.
"""

from typing import Sequence, Union

from pulumi import Input, ResourceOptions
import pulumi_aws as aws

from infralib import DeploymentContext

from .zones import DNSZonesProject


def route53_record(
    resource_name: str,
    dctx: DeploymentContext,
    name: str,
    type: Input[Union[str, aws.route53.RecordType]],
    ttl: Input[int],
    records: Input[Sequence[Input[str]]],
    opts: ResourceOptions | None = None,
) -> aws.route53.Record:
    """
    Provisions a Route 53 DNS record.

    The correct zone and provider are retrieved from the dns.zones project.

    The name on the args object must be a real Python string, not a Pulumi
    Input or Output type.
    """
    zone, provider = DNSZonesProject.lookup_zone(dctx, name)

    implicit_opts = ResourceOptions(provider=provider)
    if opts is not None:
        opts = opts.merge(implicit_opts)
    else:
        opts = implicit_opts

    return aws.route53.Record(
        resource_name,
        name=name,
        type=type,
        ttl=ttl,
        records=records,
        zone_id=zone.zone_id,
        opts=opts,
    )
