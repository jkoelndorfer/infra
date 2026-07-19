"""
infralib/config/aws -- AWS Configuration
========================================

This file defines data types for AWS-specific configuration.
"""

from typing import Any, Protocol, Self

from ..deployment.target import Environment


class MemberAccountEmailGenerator(Protocol):
    """
    Function that generates a member account email address given an environment and function.
    """

    def __call__(self, environment: Environment, function: str) -> str:
        """
        Calculates the email address for an AWS organization's member account.
        """
        raise NotImplementedError("protocol does not provide a concrete implementation")


class AWSAccount:
    """
    Configuration representing an AWS account.
    """

    def __init__(self, account_id: str) -> None:
        # The numeric ID for this account, e.g. "000000000000".
        self.account_id = account_id

    @property
    def arn(self) -> str:
        """
        The ARN for this account.
        """
        return f"arn:aws:account::{self.account_id}:account"

    @property
    def root_user_arn(self) -> str:
        """
        The ARN for the root user of this account.
        """
        return f"arn:aws:iam::{self.account_id}:root"

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Self:
        """
        Constructs an AWSAccount from a dictionary.
        """
        return cls(d["account_id"])


class AWSOrganization:
    """
    AWS organization-level configuration.
    """

    def __init__(
        self,
        organization_id: str,
        root_ou_id: str,
        management_account: AWSAccount,
        member_account_email_generator: MemberAccountEmailGenerator,
        organization_account_access_role: str,
        preferred_region: str,
        personal_iam_user: str,
        infrastructure_manager_role: str,
    ) -> None:
        # The ID of the AWS organization, e.g. "o-xxxxxxxxxx".
        self.organization_id = organization_id

        # The ID of this organization's root organizational unit, e.g. "r-xxxx".
        self.root_ou_id = root_ou_id

        # The AWSAccount that manages this organization.
        self.management_account = management_account

        # The function used to generate a member account email address.
        self.member_account_email = member_account_email_generator

        # The name of the IAM role used that the management account can use to
        # access resources in the member account.
        self.organization_account_access_role = organization_account_access_role

        # The preferred region to deploy infrastructure in.
        self.preferred_region = preferred_region

        # The IAM user used for day-to-day administration.
        self.personal_iam_user = personal_iam_user

        # The IAM role that is first assumed to make infrastructure changes.
        self.infrastructure_manager_role = infrastructure_manager_role

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs an AWSOrganization from a dictionary.
        """

        def member_email_tmpl(environment: Environment, function: str) -> str:
            result = d["member_email_template"].format(
                env=environment,
                environment=environment,
                function=function,
                fn=function,
            )
            assert isinstance(result, str)
            return result

        return cls(
            d["organization_id"],
            d["root_ou_id"],
            AWSAccount.from_dict(d["management_account"]),
            member_email_tmpl,
            d["organization_account_access_role"],
            d["preferred_region"],
            d["personal_iam_user"],
            d["infrastructure_manager_role"],
        )
