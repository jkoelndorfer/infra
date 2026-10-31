"""
projects.website.personal.s3
============================

This module contains S3 configuration for the personal website.
"""

from typing import Tuple

from pulumi import ResourceOptions
from pulumi_aws.s3 import Bucket, BucketPublicAccessBlock

from infralib import DeploymentContext

from ..s3 import private_bucket


def provision_site_bucket(
    dctx: DeploymentContext,
    account_id: str,
    aws_opts: ResourceOptions,
) -> Tuple[Bucket, BucketPublicAccessBlock]:
    """
    Provisions the S3 bucket that holds the published site.

    The contents can be republished at any time, so the bucket is not protected.
    """
    return private_bucket(
        "site_bucket",
        f"{dctx.target.environment}-personal-website-{account_id}",
        aws_opts,
    )


def provision_assets_bucket(
    dctx: DeploymentContext,
    account_id: str,
    aws_opts: ResourceOptions,
) -> Bucket:
    """
    Provisions the S3 bucket that holds additional assets, which are not
    committed to the website repository.

    This bucket is the only copy of its contents, so it is protected.
    """
    bucket, _ = private_bucket(
        "assets_bucket",
        f"{dctx.target.environment}-personal-website-assets-{account_id}",
        aws_opts,
        protect=True,
    )
    return bucket
