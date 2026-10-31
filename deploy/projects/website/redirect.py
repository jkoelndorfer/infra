"""
projects.website.redirect
=========================

This module contains a CloudFront distribution that redirects hosts to a website.
"""

import json

from pulumi import Input, ResourceOptions
from pulumi_aws.cloudfront import (
    Distribution,
    DistributionDefaultCacheBehaviorArgs as DefaultCacheBehavior,
    DistributionDefaultCacheBehaviorFunctionAssociationArgs as FunctionAssociation,
    DistributionOriginArgs as Origin,
    DistributionOriginCustomOriginConfigArgs as CustomOriginConfig,
    DistributionRestrictionsArgs as Restrictions,
    DistributionRestrictionsGeoRestrictionArgs as GeoRestriction,
    DistributionViewerCertificateArgs as ViewerCertificate,
    Function,
)

ALLOWED_METHODS = ["GET", "HEAD"]
ORIGIN_ID = "redirect_target"

# The managed "CachingDisabled" cache policy [1]. The function answers before
# the cache is consulted, so there is nothing to cache.
#
# [1]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html
CACHING_DISABLED_POLICY_ID = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"

# Query string values reach the function still percent-encoded, so they are not
# encoded again [1].
#
# [1]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/functions-event-structure.html
REDIRECT_FUNCTION = """\
function handler(event) {
    var request = event.request;
    var query = [];
    Object.keys(request.querystring).forEach(function (name) {
        var param = request.querystring[name];
        (param.multiValue || [param]).forEach(function (item) {
            query.push(item.value === "" ? name : name + "=" + item.value);
        });
    });

    return {
        statusCode: 301,
        statusDescription: "Moved Permanently",
        headers: {
            location: {
                value:
                    %(target)s +
                    request.uri +
                    (query.length ? "?" + query.join("&") : ""),
            },
        },
    };
}
"""


def provision_redirect_distribution(
    resource_name: str,
    function_name: str,
    aliases: list[str],
    target_host: str,
    certificate_arn: Input[str],
    aws_opts: ResourceOptions,
) -> Distribution:
    """
    Provisions a CloudFront distribution that answers every request to the given
    aliases with an HTTP 301 to the same path and query string on the target host.

    Plain HTTP is allowed so that those requests go straight to the target,
    rather than first being redirected to HTTPS on the alias.

    NOTE: The certificate must cover every alias.
    """
    function = Function(
        resource_name,
        name=function_name,
        comment=f"Redirects {', '.join(aliases)} to {target_host}.",
        runtime="cloudfront-js-2.0",
        code=REDIRECT_FUNCTION % {"target": json.dumps(f"https://{target_host}")},
        publish=True,
        opts=aws_opts,
    )

    return Distribution(
        resource_name,
        aliases=aliases,
        default_cache_behavior=DefaultCacheBehavior(
            allowed_methods=ALLOWED_METHODS,
            cache_policy_id=CACHING_DISABLED_POLICY_ID,
            cached_methods=ALLOWED_METHODS,
            function_associations=[
                FunctionAssociation(
                    event_type="viewer-request",
                    function_arn=function.arn,
                ),
            ],
            target_origin_id=ORIGIN_ID,
            viewer_protocol_policy="allow-all",
        ),
        enabled=True,
        is_ipv6_enabled=True,
        # CloudFront requires an origin, but the function answers every request
        # that the cache behavior allows, so this one is never contacted.
        origins=[
            Origin(
                custom_origin_config=CustomOriginConfig(
                    http_port=80,
                    https_port=443,
                    origin_protocol_policy="https-only",
                    origin_ssl_protocols=["TLSv1.2"],
                ),
                domain_name=target_host,
                origin_id=ORIGIN_ID,
            ),
        ],
        price_class="PriceClass_100",
        restrictions=Restrictions(
            geo_restriction=GeoRestriction(restriction_type="none"),
        ),
        viewer_certificate=ViewerCertificate(
            acm_certificate_arn=certificate_arn,
            minimum_protocol_version="TLSv1.2_2021",
            ssl_support_method="sni-only",
        ),
        opts=aws_opts,
    )
