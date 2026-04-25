"""
projects.aws.accounts
=====================

This module contains a project to set up AWS accounts.
"""

from typing import Self

from pulumi import export, ResourceOptions
import pulumi_aws as aws

from infralib import (
    DeploymentTarget,
    Environment,
    exportable_resource,
    InfrastructureProject,
    InfrastructureStack,
    StackOutputResolver,
)

from ..bootstrap import AWSBootstrapProject


class AWSAccount:
    """
    AWSAccount represents an AWS account created by the aws.accounts project.
    """

    def __init__(
        self,
        function: str,
        environment: Environment,
        arn: str,
        id: str,
        email: str,
        role_name: str,
    ) -> None:
        self.function = function
        self.environment = environment
        self.arn = arn
        self.id = id
        self.email = email
        self.role_name = role_name

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Self:
        return cls(
            function=d["function"],
            environment=Environment(d["environment"]),
            arn=d["arn"],
            id=d["id"],
            email=d["email"],
            role_name=d["role_name"],
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "function": self.function,
            "environment": self.environment,
            "arn": self.arn,
            "id": self.id,
            "email": self.email,
            "role_name": self.role_name,
        }

    @property
    def role_arn(self) -> str:
        return f"arn:aws:iam::{self.id}:role/{self.role_name}"


class AWSAccountsProject(InfrastructureProject):
    """
    Infrastructure project that provisions AWS accounts within the AWS organization.
    """

    name = "aws.accounts"

    env_account_fns = [
        "backup",
        "dns",
        "personal-website",
    ]

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [
            AWSBootstrapProject.stack(
                DeploymentTarget(Environment.PROD, None),
            ),
        ]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(e, None) for e in [Environment.DEV, Environment.PROD]]

    def pulumi_program(self) -> None:
        self.provider = self.dctx.provider_factory.aws_provider("mgmt")

        accounts = {a: self._account(a) for a in self.env_account_fns}

        export(
            "accounts",
            {
                k: exportable_resource(
                    acct,
                    ["arn", "id", "email", "role_name"],
                    addl={"environment": self.dctx.target.environment, "function": k},
                )
                for k, acct in accounts.items()
            },
        )

    @classmethod
    def lookup_account(
        cls,
        function: str,
        environment: Environment,
        outputs: StackOutputResolver,
    ) -> AWSAccount:
        """
        Look up the account created with the given function and environment.
        """
        stack = cls.stack(DeploymentTarget(environment, None))
        account = outputs(stack)["accounts"].value[function]

        return AWSAccount(
            function=account["function"],
            environment=account["environment"],
            arn=account["arn"],
            id=account["id"],
            email=account["email"],
            role_name=account["role_name"],
        )

    def _account(self, function: str) -> aws.organizations.Account:
        opts = ResourceOptions(ignore_changes=["role_name"], provider=self.provider)
        return aws.organizations.Account(
            function,
            name=f"{self.dctx.target.environment}-{function}",
            email=self.dctx.config.aws_organization.member_account_email(
                self.dctx.target.environment, function
            ),
            close_on_deletion=True,
            opts=opts,
            role_name=self.dctx.config.aws_organization.organization_account_access_role,
            tags={"env": self.dctx.target.environment, "function": function},
        )
