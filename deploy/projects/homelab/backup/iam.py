"""
projects.homelab.backup.iam
===========================

This module contains IAM-related configuration for backups.
"""

from dataclasses import dataclass

from pulumi import Output, InvokeOptions, ResourceOptions
import pulumi_aws as aws
from pulumi_aws.iam import (
    PolicyDocumentVersion,
    GetPolicyDocumentStatementArgs as Statement,
    PolicyStatementEffect as Effect,
)

from infralib import DeploymentContext, pcast

policy_version = PolicyDocumentVersion.POLICY_DOCUMENT_VERSION_2012_10_17

ro_bucket_actions = [
    "s3:GetBucketLocation",
    "s3:GetBucketVersioning",
    "s3:ListBucket",
    "s3:ListBucketMultipartUploads",
    "s3:ListBucketVersions",
]
"""
Actions required on an AWS bucket to permit read-only acccess to backups.
"""

ro_object_actions = [
    "s3:GetObject",
    "s3:GetObjectAttributes",
    "s3:GetObjectRetention",
    "s3:GetObjectTagging",
    "s3:GetObjectVersion",
    "s3:GetObjectVersionTagging",
]
"""
Actions required on objects to permit read-only acccess to backups.
"""

rw_object_actions = [
    *ro_object_actions,
    "s3:AbortMultipartUpload",
    "s3:DeleteObject",
    "s3:DeleteObjectTagging",
    "s3:ListMultipartUploadParts",
    "s3:PutObject",
]
"""
Actions required on objects to permit read-write acccess to backups.
"""

deny_object_actions = [
    "s3:DeleteObjectVersion",
    "s3:DeleteObjectVersionTagging",
    "s3:PutObjectVersionAcl",
    "s3:PutObjectVersionTagging",
]
"""
Actions that are explicitly denied on backup objects.
"""


deny_object_version_modification_statement = Statement(
    sid="DenyObjectVersionModification",
    effect=Effect.DENY,
    actions=deny_object_actions,
    resources=["*"],
)


@dataclass
class IAMProvisioningResult:
    """
    Class representing the result of provisioning IAM for homelab backups.
    """

    home_backup_policy: aws.iam.Policy
    """
    IAM policy enabling non-destructive writes to the S3 bucket containing backups.
    """

    deny_object_version_modification_policy: aws.iam.Policy
    """
    IAM policy that prevents previous object versions from being deleted.
    """


def provision_iam(
    dctx: DeploymentContext,
    backup_bucket_arn: Output[str],
    aws_opts: ResourceOptions,
) -> IAMProvisioningResult:
    """
    Provisions backup IAM configuration.
    """
    home_backup_policy = aws.iam.Policy(
        "home_backup",
        name="HomeBackup",
        description="Provides access for the homelab server to write to the backup bucket.",
        policy=aws.iam.get_policy_document_output(
            statements=[
                Statement(
                    sid="AllowHomeBackupBucket",
                    effect=Effect.ALLOW,
                    actions=ro_bucket_actions,
                    resources=[pcast(backup_bucket_arn)],
                ),
                Statement(
                    sid="AllowHomeBackupObjects",
                    effect=Effect.ALLOW,
                    actions=rw_object_actions,
                    resources=pcast(
                        backup_bucket_arn.apply(
                            lambda arn: [
                                f"{arn}/archive/*",
                                f"{arn}/syncthing/*",
                                f"{arn}/photoprism/*",
                                f"{arn}/restic/*",
                            ]
                        )
                    ),
                ),
                deny_object_version_modification_statement,
            ],
            version=policy_version,
            opts=InvokeOptions(provider=aws_opts.provider),
        ).json,
        opts=aws_opts,
    )

    deny_object_version_modification_policy = aws.iam.Policy(
        "deny_object_version_modification",
        name="DenyObjectVersionModification",
        description="Prevents deletion of previous bucket object versions.",
        policy=aws.iam.get_policy_document_output(
            statements=[deny_object_version_modification_statement],
            version=policy_version,
            opts=InvokeOptions(provider=aws_opts.provider),
        ).json,
        opts=aws_opts,
    )

    aws.iam.RolePolicyAttachment(
        "organization_access_deny_object_version_modification",
        policy_arn=deny_object_version_modification_policy.arn,
        role=dctx.config.aws_organization.organization_account_access_role,
        opts=aws_opts,
    )

    return IAMProvisioningResult(
        home_backup_policy,
        deny_object_version_modification_policy,
    )
