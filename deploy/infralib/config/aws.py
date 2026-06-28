"""
infralib/config/aws -- AWS Configuration
========================================

This file defines data types for AWS-specific configuration.
"""

from typing import Protocol

from ..target import Environment


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
        preferred_region: str,
        personal_iam_user: str,
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
        self.organization_account_access_role = "OrganizationAccountAccessRole"

        # The preferred region to deploy infrastructure in.
        self.preferred_region = preferred_region

        # The IAM user used for day-to-day administration.
        self.personal_iam_user = personal_iam_user
