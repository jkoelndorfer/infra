"""
projects.homelab.backup.kubernetes
==================================

This module contains Kubernetes configuration for backups.
"""

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import ServiceAccount
from pulumi_kubernetes.rbac.v1 import (
    ClusterRole,
    ClusterRoleBinding,
    PolicyRuleArgs,
    Role,
    RoleBinding,
    RoleRefArgs,
    SubjectArgs,
)

from infralib import DeploymentContext


def api_group(api_version: Output[str]) -> Output[str]:
    """
    Converts an api_version to an api_group.
    """
    return Output.from_input(api_version).apply(lambda s: s.split("/")[0])


def provision_kubernetes_sa(
    dctx: DeploymentContext,
    namespace_name: Output[str],
    k8s_opts: ResourceOptions,
) -> ServiceAccount:
    """
    Provisions the Kubernetes service account used for backups.
    """
    meta_name = f"{dctx.target.environment}-backup"

    service_account = ServiceAccount(
        "backup",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=namespace_name,
            name="backup",
        ),
        opts=k8s_opts,
    )
    service_account_subject = SubjectArgs(
        kind=service_account.kind,
        namespace=service_account.metadata.namespace,
        name=service_account.metadata.name,
    )

    cluster_role = ClusterRole(
        "backup",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=meta_name,
        ),
        rules=[
            PolicyRuleArgs(
                api_groups=["apps"],
                resources=["deployments"],
                verbs=[
                    "get",
                    "list",
                    "watch",
                ],
            ),
            PolicyRuleArgs(
                api_groups=["apps"],
                resources=["deployments/scale"],
                verbs=[
                    "patch",
                    "update",
                ],
            ),
        ],
        opts=k8s_opts,
    )

    ClusterRoleBinding(
        "backup",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=meta_name,
        ),
        role_ref=RoleRefArgs(
            api_group=api_group(cluster_role.api_version),
            kind="ClusterRole",
            name=cluster_role.metadata.name,
        ),
        subjects=[service_account_subject],
        opts=k8s_opts,
    )

    role = Role(
        "backup",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=namespace_name,
            name="backup",
        ),
        rules=[
            PolicyRuleArgs(
                api_groups=[""],
                resources=["secrets"],
                verbs=[
                    "get",
                    "list",
                ],
            ),
            PolicyRuleArgs(
                api_groups=["argoproj.io"],
                resources=["workflowtaskresults"],
                verbs=[
                    "create",
                    "get",
                    "list",
                    "patch",
                    "update",
                ],
            ),
        ],
        opts=k8s_opts,
    )

    RoleBinding(
        "backup",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=namespace_name,
            name="backup",
        ),
        role_ref=RoleRefArgs(
            api_group=api_group(role.api_version),
            kind=role.kind,
            name=role.metadata.name,
        ),
        subjects=[service_account_subject],
        opts=k8s_opts,
    )

    return service_account
