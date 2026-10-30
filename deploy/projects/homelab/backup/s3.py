"""
projects.homelab.backup.s3
==========================

This module contains S3 configuration for backups.
"""

from infralib import DeploymentContext

from pulumi import ResourceOptions
from pulumi_aws.s3 import (
    Bucket,
    BucketLifecycleConfiguration,
    BucketLifecycleConfigurationRuleArgs as Rule,
    BucketLifecycleConfigurationRuleFilterArgs as Filter,
    BucketLifecycleConfigurationRuleNoncurrentVersionExpirationArgs as NoncurrentVersionExpiration,
    BucketLifecycleConfigurationRuleTransitionArgs as Transition,
    BucketPublicAccessBlock,
    BucketVersioning,
    BucketVersioningVersioningConfigurationArgs as VersioningConfiguration,
)


def provision_backup_bucket(
    dctx: DeploymentContext,
    aws_opts: ResourceOptions,
) -> Bucket:
    """
    Provisions the S3 bucket used to store backups.
    """
    mgmt_acct_id = dctx.config.aws_organization.management_account.account_id
    bucket_name = f"{dctx.target.environment}-backup-{mgmt_acct_id}"
    backup_bucket = Bucket(
        "backup_bucket",
        bucket=bucket_name,
        opts=aws_opts.merge(
            ResourceOptions(
                import_=bucket_name,
                protect=True,
            )
        ),
    )
    BucketPublicAccessBlock(
        "backup_bucket",
        bucket=backup_bucket.bucket,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
        opts=aws_opts,
    )
    BucketVersioning(
        "backup_bucket",
        bucket=backup_bucket.bucket,
        versioning_configuration=VersioningConfiguration(
            status="Enabled",
        ),
        opts=aws_opts,
    )
    BucketLifecycleConfiguration(
        "backup_bucket",
        bucket=backup_bucket.bucket,
        rules=[
            Rule(
                id="restic-archive-data",
                status="Enabled",
                filter=Filter(
                    prefix="archive/restic/data/",
                ),
                transitions=[
                    Transition(
                        days=3,
                        storage_class="GLACIER_IR",
                    ),
                ],
            ),
            Rule(
                id="restic",
                status="Enabled",
                filter=Filter(
                    prefix="restic/",
                ),
                noncurrent_version_expiration=NoncurrentVersionExpiration(
                    noncurrent_days=30,
                ),
            ),
        ],
        opts=aws_opts,
    )

    return backup_bucket
