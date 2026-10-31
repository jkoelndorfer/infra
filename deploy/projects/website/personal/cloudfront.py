"""
projects.website.personal.cloudfront
====================================

This module contains CloudFront configuration for the personal website.
"""

from pulumi import Input, ResourceOptions
from pulumi_aws.cloudfront import (
    CachePolicy,
    CachePolicyParametersInCacheKeyAndForwardedToOriginArgs as CacheKeyParameters,
    CachePolicyParametersInCacheKeyAndForwardedToOriginCookiesConfigArgs as CookiesConfig,
    CachePolicyParametersInCacheKeyAndForwardedToOriginHeadersConfigArgs as HeadersConfig,
    CachePolicyParametersInCacheKeyAndForwardedToOriginQueryStringsConfigArgs as QueryStringsConfig,
    Distribution,
    DistributionCustomErrorResponseArgs as CustomErrorResponse,
    DistributionDefaultCacheBehaviorArgs as DefaultCacheBehavior,
    DistributionOrderedCacheBehaviorArgs as OrderedCacheBehavior,
    DistributionOriginArgs as Origin,
    DistributionRestrictionsArgs as Restrictions,
    DistributionRestrictionsGeoRestrictionArgs as GeoRestriction,
    DistributionViewerCertificateArgs as ViewerCertificate,
    OriginAccessControl,
)
from pulumi_aws.s3 import Bucket

from infralib import DeploymentContext

ALLOWED_METHODS = ["GET", "HEAD", "OPTIONS"]
ORIGIN_ID = "site"


def _cache_policy(
    dctx: DeploymentContext,
    name: str,
    min_ttl: int,
    default_ttl: int,
    max_ttl: int,
    aws_opts: ResourceOptions,
) -> CachePolicy:
    """
    Provisions a cache policy that keys only on the path, since the site is
    static and uses neither cookies nor query strings.
    """
    return CachePolicy(
        f"{name}_cache_policy",
        name=f"{dctx.target.environment}-personal-website-{name}",
        min_ttl=min_ttl,
        default_ttl=default_ttl,
        max_ttl=max_ttl,
        parameters_in_cache_key_and_forwarded_to_origin=CacheKeyParameters(
            cookies_config=CookiesConfig(cookie_behavior="none"),
            enable_accept_encoding_brotli=True,
            enable_accept_encoding_gzip=True,
            headers_config=HeadersConfig(header_behavior="none"),
            query_strings_config=QueryStringsConfig(query_string_behavior="none"),
        ),
        opts=aws_opts,
    )


def provision_distribution(
    dctx: DeploymentContext,
    aliases: list[str],
    bucket: Bucket,
    certificate_arn: Input[str],
    aws_opts: ResourceOptions,
) -> Distribution:
    """
    Provisions the CloudFront distribution that serves the site bucket.

    The origin is the bucket's REST endpoint, so an index document is only served
    at the site root: "/about/" does not resolve to "/about/index.html".
    """
    origin_access_control = OriginAccessControl(
        "site",
        name=f"{dctx.target.environment}-personal-website",
        description="Permits CloudFront to read the personal website bucket.",
        origin_access_control_origin_type="s3",
        signing_behavior="always",
        signing_protocol="sigv4",
        opts=aws_opts,
    )
    default_cache_policy = _cache_policy(
        dctx,
        "default",
        min_ttl=0,
        default_ttl=600,
        max_ttl=1800,
        aws_opts=aws_opts,
    )
    fonts_cache_policy = _cache_policy(
        dctx,
        "fonts",
        min_ttl=3600,
        default_ttl=604800,
        max_ttl=604800,
        aws_opts=aws_opts,
    )

    return Distribution(
        "site",
        aliases=aliases,
        custom_error_responses=[
            CustomErrorResponse(
                error_caching_min_ttl=60,
                error_code=404,
                response_code=404,
                response_page_path="/404.html",
            ),
        ],
        default_cache_behavior=DefaultCacheBehavior(
            allowed_methods=ALLOWED_METHODS,
            cache_policy_id=default_cache_policy.id,
            cached_methods=ALLOWED_METHODS,
            compress=True,
            target_origin_id=ORIGIN_ID,
            viewer_protocol_policy="redirect-to-https",
        ),
        default_root_object="index.html",
        enabled=True,
        is_ipv6_enabled=True,
        ordered_cache_behaviors=[
            OrderedCacheBehavior(
                allowed_methods=ALLOWED_METHODS,
                cache_policy_id=fonts_cache_policy.id,
                cached_methods=ALLOWED_METHODS,
                compress=True,
                path_pattern="/fonts/*",
                target_origin_id=ORIGIN_ID,
                viewer_protocol_policy="redirect-to-https",
            ),
        ],
        origins=[
            Origin(
                domain_name=bucket.bucket_regional_domain_name,
                origin_access_control_id=origin_access_control.id,
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
