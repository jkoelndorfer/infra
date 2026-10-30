"""
projects.homelab.backup.kserv
=============================

This module contains kserv configuration for backups.
"""

from pulumi import Output, ResourceOptions
import pulumi_aws as aws
import pulumi_kubernetes as k8s

from infralib import DeploymentContext

from .iam import IAMProvisioningResult


def provision_kserv_backup(
    dctx: DeploymentContext,
    namespace_name: Output[str],
    iam_provisioning_result: IAMProvisioningResult,
    aws_opts: ResourceOptions,
    k8s_opts: ResourceOptions,
) -> None:
    """
    Provisions configuration for kserv backups.
    """

    kserv_iam_user = aws.iam.User(
        "kserv",
        name="kserv-backup",
        opts=aws_opts,
    )

    kserv_iam_user_access_key = aws.iam.AccessKey(
        "kserv",
        user=kserv_iam_user.name,
        opts=aws_opts,
    )

    aws.iam.UserPolicyAttachment(
        "kserv_backup",
        policy_arn=iam_provisioning_result.home_backup_policy.arn,
        user=kserv_iam_user.name,
        opts=aws_opts,
    )

    aws.iam.UserPolicyAttachment(
        "kserv_deny_object_version_modification",
        policy_arn=iam_provisioning_result.deny_object_version_modification_policy.arn,
        user=kserv_iam_user.name,
        opts=aws_opts,
    )

    k8s.core.v1.Secret(
        "aws_backup",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=namespace_name,
            name="aws-backup",
        ),
        string_data={
            "aws_access_key_id": kserv_iam_user_access_key.id,
            "aws_secret_access_key": kserv_iam_user_access_key.secret,
        },
        opts=k8s_opts,
    )

    # NOTE: The "restic" secret needs to be added to the backup namespace
    # with a "repository_password" data. This ensures that the backup
    # password isn't stored in the state file.
    #
    # A resource is below. Replace the variables by their appropriate values
    # and then run `kubectl apply -f /path/to/resource.yaml`.
    #
    # ---
    # apiVersion: v1
    # data:
    #   archive_repository_password: ${BASE64_ENCODED_ARCHIVE_REPOSITORY_PASSWORD}
    #   repository_password:         ${BASE64_ENCODED_REPOSITORY_PASSWORD}
    # kind: Secret
    # metadata:
    #   name: restic
    #   namespace: ${NAMESPACE}
