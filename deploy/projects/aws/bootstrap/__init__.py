"""
projects.aws.bootstrap
======================

This module contains a project to bootstrap AWS.
"""

from dataclasses import dataclass

from pulumi import export, InvokeOptions, ResourceOptions
import pulumi_aws as aws

from infralib import (
    DeploymentContext,
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
    pcast,
)


@dataclass
class AWSIdentityCenterAccess:
    """
    The values required to grant the Identity Center user access to an account.
    """

    instance_arn: str
    permission_set_arn: str
    user_id: str


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
        self.configure_organization_mgmt_policy()
        self.configure_infrastructure_manager_role()
        self.configure_personal_user()
        self.configure_identity_center()

    @classmethod
    def lookup_identity_center_access(
        cls,
        dctx: DeploymentContext,
    ) -> AWSIdentityCenterAccess:
        """
        Look up the values required to grant the Identity Center user access to
        an account.
        """
        stack = cls.stack(DeploymentTarget(Environment.PROD, None))
        access = dctx.outputs(stack)["identity_center_access"].value
        return AWSIdentityCenterAccess(
            instance_arn=access["instance_arn"],
            permission_set_arn=access["permission_set_arn"],
            user_id=access["user_id"],
        )

    def configure_infrastructure_manager_role(self) -> None:
        assume_role_policy = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    effect="Allow",
                    actions=["sts:AssumeRole"],
                    principals=[
                        aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                            type="AWS",
                            identifiers=[
                                self.dctx.config.aws_organization.management_account.root_user_arn,
                            ],
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

    def configure_identity_center(self) -> None:
        """
        Creates the permission set used to sign in with read-only access and
        assume the organization access role in member accounts.

        This assigns the permission set to the management account. aws.accounts
        assigns it to each member account.

        NOTE: Identity Center must be enabled by hand in the preferred region,
        and the user must be created by hand with their email address as their
        username.
        """
        instances = aws.ssoadmin.get_instances(opts=self.default_iopts)
        instance_arn = instances.arns[0]
        user = aws.identitystore.get_user(
            identity_store_id=instances.identity_store_ids[0],
            alternate_identifier=aws.identitystore.GetUserAlternateIdentifierArgs(
                unique_attribute=aws.identitystore.GetUserAlternateIdentifierUniqueAttributeArgs(
                    attribute_path="UserName",
                    attribute_value=self.dctx.config.aws_organization.sso_user,
                ),
            ),
            opts=self.default_iopts,
        )
        permission_set = aws.ssoadmin.PermissionSet(
            "read_only_member_account_access",
            name="ReadOnlyMemberAccountAccess",
            description="Grants read-only access and access to manage organization member accounts.",
            instance_arn=instance_arn,
            opts=self.default_ropts,
        )
        ro_policy = aws.iam.get_policy_output(
            name="ReadOnlyAccess",
            opts=self.default_iopts,
        )
        ro_attachment = aws.ssoadmin.ManagedPolicyAttachment(
            "read_only_member_account_access_ro",
            instance_arn=instance_arn,
            managed_policy_arn=ro_policy.arn,
            permission_set_arn=permission_set.arn,
            opts=self.default_ropts,
        )
        # This is inline because a permission set can only reference a customer
        # managed policy that exists in every account it is assigned to, and the
        # OrganizationMemberAccountAccess policy only exists in this account.
        inline_policy = aws.ssoadmin.PermissionSetInlinePolicy(
            "read_only_member_account_access_assume",
            inline_policy=self.org_member_access_policy_doc.json,
            instance_arn=instance_arn,
            permission_set_arn=permission_set.arn,
            opts=self.default_ropts,
        )
        # The organization access role only trusts the management account, so it
        # can only be assumed from a session in that account.
        aws.ssoadmin.AccountAssignment(
            "read_only_member_account_access_management",
            instance_arn=instance_arn,
            permission_set_arn=permission_set.arn,
            principal_id=user.user_id,
            principal_type="USER",
            target_id=self.dctx.config.aws_organization.management_account.account_id,
            target_type="AWS_ACCOUNT",
            opts=ResourceOptions(
                provider=self.aws_provider,
                depends_on=[ro_attachment, inline_policy],
            ),
        )
        export(
            "identity_center_access",
            {
                "instance_arn": instance_arn,
                "permission_set_arn": permission_set.arn,
                "user_id": user.user_id,
            },
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
                ),
                aws.iam.GetPolicyDocumentStatementArgs(
                    sid="AllowIdentityCenterAccountAssignment",
                    effect="Allow",
                    actions=[
                        "sso:CreateAccountAssignment",
                        "sso:DeleteAccountAssignment",
                        "sso:DescribeAccountAssignmentCreationStatus",
                        "sso:DescribeAccountAssignmentDeletionStatus",
                        "sso:ListAccountAssignments",
                    ],
                    resources=["*"],
                ),
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
        self.org_member_access_policy_doc = aws.iam.get_policy_document(
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
            policy=self.org_member_access_policy_doc.json,
            opts=self.default_ropts,
        )
