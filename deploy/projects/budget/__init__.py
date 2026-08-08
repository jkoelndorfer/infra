"""
projects.budget
===============

This module contains an InfrastructureProject that configures cloud spend budgets.
"""

from typing import Literal, Protocol

from pulumi import ResourceOptions
import pulumi_aws as aws
import pulumi_gcp as gcp

from infralib import (
    DeploymentTarget,
    EmailChannel,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
    NotificationCategory,
    to_logical_name,
)

from ..aws.bootstrap import AWSBootstrapProject
from ..gcp.bootstrap import GCPBootstrapProject

AWSNotificationType = Literal["ACTUAL", "FORECASTED"]


class AWSNotificationFn(Protocol):
    """
    Protocol for a function producing an AWS budget notification.
    """

    def __call__(
        self,
        threshold_pct: float,
        notification_type: AWSNotificationType,
    ) -> aws.budgets.BudgetNotificationArgs:
        raise NotImplementedError("protocol does not provide concrete implementation")


class BudgetProject(InfrastructureProject):
    """
    Infrastructure project that configures cloud budgets.
    """

    name = "budget"

    # The monthly spend limit for AWS in US Dollars.
    MONTHLY_SPEND_LIMIT_AWS_USD = 10

    # The monthly spend limit for GCP in US Dollars.
    MONTHLY_SPEND_LIMIT_GCP_USD = 5

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [
            AWSBootstrapProject.stack(target),
            GCPBootstrapProject.stack(target),
        ]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.PROD, None),
        ]

    def pulumi_program(self) -> None:
        self._configure_aws_budget()
        self._configure_gcp_budget()

    def _configure_aws_budget(self) -> None:
        aws_provider = self.dctx.provider_factory.aws_provider("aws")
        aws_notification = self._make_aws_notification_fn()
        aws.budgets.Budget(
            "aws_budget",
            name="Budget",
            budget_type="COST",
            limit_amount=str(self.MONTHLY_SPEND_LIMIT_AWS_USD),
            limit_unit="USD",
            time_unit="MONTHLY",
            notifications=[
                aws_notification(
                    threshold_pct=100.0,
                    notification_type="FORECASTED",
                ),
                aws_notification(
                    threshold_pct=100.0,
                    notification_type="ACTUAL",
                ),
                aws_notification(
                    threshold_pct=200.0,
                    notification_type="ACTUAL",
                ),
            ],
            opts=ResourceOptions(provider=aws_provider),
        )

    def _configure_gcp_budget(self) -> None:
        gcp_provider = self.dctx.provider_factory.gcp_provider()
        gcp_bootstrap_output = self.dctx.outputs(
            GCPBootstrapProject.stack(self.dctx.target)
        )
        infra_mgmt_project = gcp_bootstrap_output["infra_mgmt_project"]

        gcp_channels: list[gcp.monitoring.NotificationChannel] = list()
        for channel in self._budget_email_channels():
            channel_resource = gcp.monitoring.NotificationChannel(
                to_logical_name(channel.name),
                display_name=channel.name,
                type="email",
                project=infra_mgmt_project.value["project_id"],
                labels={"email_address": channel.email},
                opts=ResourceOptions(provider=gcp_provider),
            )
            gcp_channels.append(channel_resource)

        # NOTE: It seems that budget alerts do not support Google Chat
        # notification channels.
        #
        # When I try to provision one, I receive the error:
        #
        #
        #   googleapi: Error 400: Request contains an invalid argument.
        #
        #
        # So we just use email here.
        gcp.billing.Budget(
            "gcp_budget",
            billing_account=self.dctx.config.gcp_organization.billing_account_id,
            display_name="Budget",
            budget_filter=gcp.billing.BudgetBudgetFilterArgs(
                credit_types_treatment="EXCLUDE_ALL_CREDITS",
            ),
            amount=gcp.billing.BudgetAmountArgs(
                specified_amount=gcp.billing.BudgetAmountSpecifiedAmountArgs(
                    currency_code="USD",
                    units=str(self.MONTHLY_SPEND_LIMIT_GCP_USD),
                ),
            ),
            threshold_rules=[
                gcp.billing.BudgetThresholdRuleArgs(
                    threshold_percent=1.0,
                    spend_basis="CURRENT_SPEND",
                ),
                gcp.billing.BudgetThresholdRuleArgs(
                    threshold_percent=2.0,
                    spend_basis="CURRENT_SPEND",
                ),
                gcp.billing.BudgetThresholdRuleArgs(
                    threshold_percent=1.0,
                    spend_basis="FORECASTED_SPEND",
                ),
            ],
            all_updates_rule=gcp.billing.BudgetAllUpdatesRuleArgs(
                monitoring_notification_channels=[c.name for c in gcp_channels],
                disable_default_iam_recipients=True,
            ),
            opts=ResourceOptions(
                provider=gcp_provider,
            ),
        )

    def _budget_email_channels(self) -> list[EmailChannel]:
        email_channels: list[EmailChannel] = list()
        for c in self.dctx.config.notification_channels:
            if not isinstance(c, EmailChannel):
                continue
            if c.category != NotificationCategory.CLOUD_BILLING:
                continue
            email_channels.append(c)
        return email_channels

    def _make_aws_notification_fn(self) -> AWSNotificationFn:
        def aws_notification(
            threshold_pct: float, notification_type: AWSNotificationType
        ) -> aws.budgets.BudgetNotificationArgs:
            return aws.budgets.BudgetNotificationArgs(
                comparison_operator="GREATER_THAN",
                threshold=threshold_pct,
                threshold_type="PERCENTAGE",
                notification_type=notification_type,
                subscriber_email_addresses=[
                    c.email for c in self._budget_email_channels()
                ],
            )

        return aws_notification
