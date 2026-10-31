"""
projects.website.personal.s3
============================

This module contains S3 configuration for the personal website.
"""

from typing import Any, Tuple

from pulumi import Output, ResourceOptions
from pulumi_aws.cloudfront import Distribution
from pulumi_aws.s3 import Bucket, BucketPolicy, BucketPublicAccessBlock

from infralib import DeploymentContext


def _private_bucket(
    resource_name: str,
    bucket_name: str,
    aws_opts: ResourceOptions,
    protect: bool = False,
) -> Tuple[Bucket, BucketPublicAccessBlock]:
    """
    Provisions an S3 bucket that blocks all public access.
    """
    bucket = Bucket(
        resource_name,
        bucket=bucket_name,
        opts=aws_opts.merge(ResourceOptions(protect=protect)),
    )
    access_block = BucketPublicAccessBlock(
        resource_name,
        bucket=bucket.bucket,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
        opts=aws_opts,
    )
    return (bucket, access_block)


def provision_site_bucket(
    dctx: DeploymentContext,
    account_id: str,
    aws_opts: ResourceOptions,
) -> Tuple[Bucket, BucketPublicAccessBlock]:
    """
    Provisions the S3 bucket that holds the published site.

    The contents can be republished at any time, so the bucket is not protected.
    """
    return _private_bucket(
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
    bucket, _ = _private_bucket(
        "assets_bucket",
        f"{dctx.target.environment}-personal-website-assets-{account_id}",
        aws_opts,
        protect=True,
    )
    return bucket


def provision_site_bucket_policy(
    bucket: Bucket,
    access_block: BucketPublicAccessBlock,
    distribution: Distribution,
    aws_opts: ResourceOptions,
) -> BucketPolicy:
    """
    Provisions the bucket policy that permits only the given distribution to
    read the site bucket [1].

    s3:ListBucket makes S3 answer 404 instead of 403 for a missing object, which
    the distribution's custom error response relies on.

    [1]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
    """

    def statement(action: str, resource: Output[str]) -> dict[str, Any]:
        return {
            "Effect": "Allow",
            "Principal": {"Service": "cloudfront.amazonaws.com"},
            "Action": action,
            "Resource": resource,
            "Condition": {"StringEquals": {"AWS:SourceArn": distribution.arn}},
        }

    return BucketPolicy(
        "site_bucket",
        bucket=bucket.bucket,
        policy=Output.json_dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    statement("s3:GetObject", Output.concat(bucket.arn, "/*")),
                    statement("s3:ListBucket", bucket.arn),
                ],
            }
        ),
        # S3 rejects concurrent changes to a bucket's policy and public access
        # block.
        opts=aws_opts.merge(ResourceOptions(depends_on=[access_block])),
    )
