===============
Bootstrap Stack
===============

This stack provides initial setup for Amazon Web Services and Google Cloud
Platform infrastructure. It is intended to be run in completely fresh
organizations with minimal configuration.

**Note that the state files for all bootstrapping units are stored in-repo!
It is imperative that secret resources are not managed as part of the
bootstrapping process!**

Prerequisites
=============

Before applying the bootstrap stack, ensure the prerequisites are met for
both AWS and GCP.

GCP Prerequisites
-----------------

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

AWS Prerequisites
-----------------

Configure a master account that manages an
[AWS Organization](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html).

To perform initial setup, the root user of the master account will need credentials (such
as access keys) that Terraform can use to provision resources.

Store the access key for the management account root in the AWS shared credential file
as specified in `terragrunt/root.hcl`.

Bootstrapping
=============

Bootstrapping GCP
-----------------

Ensure the `gcloud` CLI is configured to authenticate using a
principal that has sufficient permissions as described in the
*GCP Prerequisites* section.

Under the `bootstrap` stack, apply the `google_bootstrap` unit:

```
$ cd terragrunt/stacks/bootstrap
$ terragrunt stack clean && terragrunt stack generate
$ (cd .terragrunt-stack/google_bootstrap && terragrunt run apply)
```

The `bootstrap` stack should apply in a single pass. If this is a
brand new GCP organization, a service account key will appear in
the Terragrunt credentials file specified in `root.hcl`. If not,
you'll need to taint the credential resource (to force generation
of a new one) or put a previously-generated key in the required
location manually.

Bootstrapping AWS
-----------------

Due to limitations with Terraform's AWS provider and AWS itself,
bootstrapping is a multi-phase process.

Ensure the AWS shared credential file has a credential for the
organization management account's root user.

Under the `bootstrap` stack, apply the `aws_bootstrap` unit:

```
$ cd terragrunt/stacks/bootstrap
$ terragrunt stack clean && terragrunt stack generate
$ (cd .terragrunt-stack/aws_bootstrap && terragrunt run apply)
```

Next, create access credentials for the created `terragrunt` IAM user
in the organization master account. Add the credentials to the AWS
shared credential file in accordance with the instructions in `root.hcl`.

Finally, finish AWS bootstrapping by applying the `aws_infra_mgmt` unit.

```
$ (cd .terragrunt-stack/aws_infra_mgmt && terragrunt run apply)
```

Post-Bootstrap
--------------

The bootstrap stack creates some Secret Manager secrets within infra-mgmt that
other stacks use to gain access to sensitive information. The bootstrap stack
*does not* populate values for the secrets.

Create a secret version for each secret and ensure it contains an appropriate
value.

Delete the no-longer-necessary organization root user IAM credentials in the AWS
console.

[1]: https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment
