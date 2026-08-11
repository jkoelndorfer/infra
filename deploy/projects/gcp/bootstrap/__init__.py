"""
projects.gcp.bootstrap
======================

This module contains a project to bootstrap GCP.
"""

from pulumi import ResourceOptions
import pulumi_gcp as gcp

from infralib import (
    DeploymentTarget,
    Environment,
    export_resource,
    InfrastructureProject,
    InfrastructureStack,
)


class GCPBootstrapProject(InfrastructureProject):
    """
    Project that bootstraps GCP.

    This project configures core organization settings and provisions IAM
    access for a personal user. Because this project requires elevated permissions,
    it is required that you apply it organization administrator credentials.
    """

    name = "gcp.bootstrap"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [
            DeploymentTarget(Environment.PROD, None),
        ]

    def pulumi_program(self) -> None:
        self.gcp_provider = gcp.Provider("gcp")
        self.default_ropts = ResourceOptions(provider=self.gcp_provider)
        self._configure_infra_mgmt_project()
        self._configure_infra_mgmt_service_account()
        self._configure_personal_iam()
        self._configure_organization_policies()

        export_resource(
            name="infra_mgmt_project",
            resource=self.infra_mgmt_project,
            attrs=[
                "id",
                "number",
                "org_id",
                "project_id",
            ],
        )

    def _configure_infra_mgmt_project(self) -> None:
        infra_mgmt_project_services = [
            # This is needed to create a billing budget.
            "billingbudgets.googleapis.com",
            # This is needed to associate projects to a billing account.
            "cloudbilling.googleapis.com",
            # This is needed to create folders and projects.
            "cloudresourcemanager.googleapis.com",
            # This is needed to create custom IAM roles.
            "iam.googleapis.com",
            # This is needed to enable budget-related notifications.
            "monitoring.googleapis.com",
            # This is needed to enable the v2 organization policy API.
            "orgpolicy.googleapis.com",
            # This is needed to enable Secret Manager secret creation in infra-mgmt.
            "secretmanager.googleapis.com",
            # This is needed so that APIs can be enabled on created projects.
            # See https://github.com/hashicorp/terraform-provider-google/issues/1538#issuecomment-392127015.
            "serviceusage.googleapis.com",
        ]

        gcp_org = self.dctx.config.gcp_organization

        self.infra_mgmt_project = gcp.organizations.Project(
            "infra_mgmt_project",
            name="infra-mgmt",
            project_id=f"infra-mgmt-{gcp_org.organization_id}",
            billing_account=gcp_org.billing_account_id,
            org_id=gcp_org.organization_id,
            auto_create_network=False,
            deletion_policy="DELETE",
            opts=self.default_ropts,
        )
        for s in infra_mgmt_project_services:
            service_resource = gcp.projects.Service(
                f"infra_mgmt_project.service/{s}",
                project=self.infra_mgmt_project.project_id,
                service=s,
                opts=self.default_ropts,
            )
            if s == "orgpolicy.googleapis.com":
                self.orgpolicy_service = service_resource

    def _configure_infra_mgmt_service_account(self) -> None:
        org_iam_roles = [
            "roles/resourcemanager.folderCreator",
            "roles/resourcemanager.projectCreator",
        ]

        billing_account_roles = [
            # Required to allow newly created projects to be associated with
            # the billing account.
            #
            # See https://cloud.google.com/billing/docs/how-to/billing-access.
            "roles/billing.user",
            "roles/billing.costsManager",
        ]

        infra_mgmt_project_roles = [
            "roles/secretmanager.secretAccessor",
            "roles/serviceusage.serviceUsageConsumer",
            "roles/monitoring.notificationChannelEditor",
        ]
        infra_mgmt_sa = gcp.serviceaccount.Account(
            "infra_mgmt",
            account_id="infra-mgmt",
            display_name="infra-mgmt",
            description="Used to manage infrastructure using automated tooling.",
            project=self.infra_mgmt_project.project_id,
            opts=self.default_ropts,
        )
        for r in org_iam_roles:
            gcp.organizations.IAMMember(
                f"infra_mgmt_sa.org.{r}",
                org_id=self.dctx.config.gcp_organization.organization_id,
                role=r,
                member=infra_mgmt_sa.member,
                opts=self.default_ropts,
            )
        for r in infra_mgmt_project_roles:
            gcp.projects.IAMMember(
                f"infra_mgmt_sa.project.{r}",
                project=self.infra_mgmt_project.project_id,
                role=r,
                member=infra_mgmt_sa.member,
                opts=self.default_ropts,
            )

        for r in billing_account_roles:
            gcp.billing.AccountIamMember(
                f"infra_mgmt_sa.billing.{r}",
                billing_account_id=self.dctx.config.gcp_organization.billing_account_id,
                role=r,
                member=infra_mgmt_sa.member,
                opts=self.default_ropts,
            )

    def _configure_personal_iam(self) -> None:
        personal_iam_roles = [
            "roles/billing.viewer",
            "roles/iam.organizationRoleViewer",
            "roles/orgpolicy.policyViewer",
            "roles/resourcemanager.folderViewer",
            "roles/viewer",
        ]
        for role in personal_iam_roles:
            gcp.organizations.IAMMember(
                f"personal_iam.{role}",
                org_id=self.dctx.config.gcp_organization.organization_id,
                role=role,
                member=f"user:{self.dctx.config.gcp_organization.personal_iam_user}",
                opts=self.default_ropts,
            )

    def _configure_organization_policies(self) -> None:
        gcp_quota = gcp.Provider(
            "gcp_quota",
            billing_project=self.infra_mgmt_project.project_id,
            project=self.infra_mgmt_project.project_id,
            user_project_override=True,
        )
        enforced_constraints = [
            # When new GCP projects are created, skip creating a default VPC network.
            "compute.skipDefaultNetworkCreation",
            # When new GCP projects are created, prevent default service accounts from
            # receiving the very broad "Editor" IAM grant.
            "iam.automaticIamGrantsForDefaultServiceAccounts",
            "iam.managed.preventPrivilegedBasicRolesForDefaultServiceAccounts",
        ]
        org_id = self.dctx.config.gcp_organization.organization_id

        for c in enforced_constraints:
            gcp.orgpolicy.Policy(
                f"enforced_constraint/{c}",
                name=f"organizations/{org_id}/policies/{c}",
                parent=f"organizations/{org_id}",
                spec=gcp.orgpolicy.PolicySpecArgs(
                    rules=[
                        gcp.orgpolicy.PolicySpecRuleArgs(
                            enforce="TRUE",
                        ),
                    ],
                ),
                opts=ResourceOptions(
                    provider=gcp_quota,
                    depends_on=[
                        self.infra_mgmt_project,
                        self.orgpolicy_service,
                    ],
                ),
            )
