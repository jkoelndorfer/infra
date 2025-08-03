Bootstrap Stack
===============

This stack provides initial setup for Google Cloud Platform. It is intended
to be run in a completely fresh organization with minimal configuration.

Prerequisites
-------------

First, configure a billing account. Ensure its ID is accurate in Terragrunt's
`root.hcl`.

Because no cloud resources exist yet, this stack uses local application
default credentials. Run `gcloud auth application-default login` to
configure credentials [1]. The application default credential principal
requires fairly extensive permissions, so a simple "superuser" approach
is recommended. The following roles will enable the bootstrap stack to
apply successfully:

- `roles/billing.admin`: to associate the infra-mgmt project to the billing account
- `roles/orgpolicy.policyAdmin`: to configure organization-wide constraints
- `roles/owner`: to manage the infra-mgmt project after it is created
- `roles/resourcemanager.folderAdmin`: to manage environment-specific folders
- `roles/resourcemanager.organizationAdmin`: to manage organization IAM policies
- `roles/resourcemanager.projectCreator`: to create the infra-mgmt project at the top level of the organization

Post-Bootstrap
--------------

The bootstrap stack creates some Secret Manager secrets within infra-mgmt that 
other stacks use to gain access to sensitive information. The bootstrap stack
*does not* populate values for the secrets.

Create a secret version for each secret and ensure it contains an appropriate
value.

[1]: https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment
