"""
projects.aws.bootstrap
======================

This module contains a project to bootstrap AWS.
"""

from pulumi import InvokeOptions, ResourceOptions
import pulumi_aws as aws

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
    pcast,
)


class AWSBootstrapProject(InfrastructureProject):
    """
    Project that bootstraps AWS.

    This project configures permissions required for basic organization function
    on the management account. Because this project requires elevated permissions
    in the management account, it uses a profile specifically for the root user.

    Root user credentials should be deleted once bootstrapping is complete.
    """

    name = "aws.bootstrap"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.PROD, None),
        ]

    def pulumi_program(self) -> None:
        self.aws_provider = aws.Provider(
            "root",
            profile="root",
            region=self.dctx.config.aws_organization.preferred_region,
        )
        self.default_iopts = InvokeOptions(provider=self.aws_provider)
        self.default_ropts = ResourceOptions(provider=self.aws_provider)
        self.org_id = self.dctx.config.aws_organization.management_account.account_id
        self.configure_member_account_access_policy()
        self.configure_infrastructure_manager_role()
        self.configure_personal_user()

    def configure_infrastructure_manager_role(self) -> None:
        assume_role_policy = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    effect="Allow",
                    actions=["sts:AssumeRole"],
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="AWS",
                            identifiers=self.dctx.config.aws_organization.management_account.root_user_arn,
                        ),
                    ],
                ),
            ],
            opts=self.default_iopts,
        )
        infra_mgr_role = aws.iam.Role(
            "infrastructure_manager",
            name="InfrastructureManager",
            description="Role that permits managing infrastructure for the organization.",
            assume_role_policy=assume_role_policy.json,
            opts=self.default_ropts,
        )
        policy_doc = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    sid="AllowAssumeRole",
                    effect=aws.iam.PolicyStatementEffect.ALLOW,
                    actions=["sts:AssumeRole"],
                    resources=[pcast(infra_mgr_role.arn)],
                )
            ],
            opts=self.default_iopts,
        )
        self.infra_mgr_assume_policy = aws.iam.Policy(
            "assume_infrastructure_manager_role",
            name="AssumeInfrastructureManagerRole",
            path="/",
            description="Grants access to assume the InfrastructureManager role.",
            policy=policy_doc.json,
            opts=self.default_ropts,
        )

    def configure_personal_user(self) -> None:
        personal_user = aws.iam.User(
            "personal_user",
            name=self.dctx.config.aws_organization.personal_iam_user,
            opts=ResourceOptions(
                provider=self.aws_provider,
                import_=self.dctx.config.aws_organization.personal_iam_user,
                ignore_changes=["tags", "tagsAll"],
            ),
        )
        ro_policy = aws.iam.get_policy_output(
            name="ReadOnlyAccess",
            opts=self.default_iopts,
        )
        aws.iam.UserPolicyAttachment(
            "personal_user_ro",
            policy_arn=ro_policy.arn,
            user=personal_user.name,
            opts=self.default_ropts,
        )
        aws.iam.UserPolicyAttachment(
            "personal_user_assume_infrastructure_manager",
            policy_arn=self.infra_mgr_assume_policy.arn,
            user=personal_user.name,
            opts=self.default_ropts,
        )
        aws.iam.UserPolicyAttachment(
            "personal_user_member_account_access",
            policy_arn=self.org_member_access_policy.arn,
            user=personal_user.name,
            opts=self.default_ropts,
        )

    def configure_organization_mgmt_policy(self) -> None:
        policy_doc = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    sid="AllowOrganizationManagement",
                    effect="Allow",
                    actions=[
                        "organizations:CloseAccount",
                        "organizations:CreateAccount",
                        "organizations:CreateOrganizationalUnit",
                        "organizations:DescribeAccount",
                        "organizations:DescribeCreateAccountStatus",
                        "organizations:DescribeOrganization",
                        "organizations:DescribeOrganizationalUnit",
                        "organizations:ListAccounts",
                        "organizations:ListAccountsForParent",
                        "organizations:ListCreateAccountStatus",
                        "organizations:ListOrganizationalUnitsForParent",
                        "organizations:ListParents",
                        "organizations:ListTagsForResource",
                        "organizations:MoveAccount",
                        "organizations:TagResource",
                        "organizations:UntagResource",
                        "organizations:UpdateOrganizationalUnit",
                    ],
                    resources=["*"],
                )
            ],
            opts=self.default_iopts,
        )
        aws.iam.Policy(
            "infra_mgmt_organization_access",
            name="InfrastructureManagementOrganizationAccess",
            path="/",
            description="Grants access for infrastructure management tooling to manage the organization.",
            policy=policy_doc.json,
            opts=self.default_ropts,
        )

    def configure_member_account_access_policy(self) -> None:
        member_role = self.dctx.config.aws_organization.organization_account_access_role
        policy_doc = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    sid="AllowOrganizationAssumeRole",
                    effect="Allow",
                    actions=["sts:AssumeRole"],
                    resources=[f"arn:aws:iam::*:role/{member_role}"],
                )
            ],
            opts=self.default_iopts,
        )
        self.org_member_access_policy = aws.iam.Policy(
            "organization_member_account_access",
            name="OrganizationMemberAccountAccess",
            path="/",
            description="Grants access to manage organization member accounts.",
            policy=policy_doc.json,
            opts=self.default_ropts,
        )
