locals {
  repo_root       = get_repo_root()
  terragrunt_root = "${local.repo_root}/terragrunt"

  # Path to the directory containing local service account
  # credentials for Terragrunt.
  terragrunt_credentials = pathexpand("~/.local/terragrunt/credentials")

  _aws_management_account_id = "780570912590"
  _aws_organization_id = "o-rdbgkdyowc"
  _aws_root_ou_id = "r-sict"

  aws_organization = {
    id                 = local._aws_organization_id
    default_region     = "us-east-2"
    master_account_arn = "arn:aws:account::${local._aws_management_account_id}:account"
    master_account_id  = local._aws_management_account_id

    root_ou = {
      id  = local._aws_root_ou_id
      arn = "arn:aws:organizations::${local._aws_management_account_id}:root/${local._aws_organization_id}/${local._aws_root_ou_id}"
    }

    # The name of the IAM role used that the management account can use to
    # access resources in the member account.
    member_account_access_role = "OrganizationAccountAccessRole"

    # Template string used to create the owner email for
    # AWS organization member accounts.
    #
    # NOTE: this needs to be double-escaped because it is rendered to JSON, where a string
    # containing "${...}" is treated as a resource reference.
    member_account_email_tmpl = "aws.$$${identifier}@john.$$${google_organization_domain}"
  }

  # Mirrors the structure of the google_organization data; see
  # https://registry.terraform.io/providers/hashicorp/google/6.46.0/docs/data-sources/organization.
  google_organization = {
    org_id = "285001668841"
    domain = "koelndorfer.com"
  }

  # Mirrors the structure of the google_billing_account data; see
  # https://registry.terraform.io/providers/hashicorp/google/6.46.0/docs/data-sources/billing_account.
  google_billing_account = {
    id = "018603-0A0108-775C8E"
  }

  # Mirrors the structure of the google_project data; see
  # https://registry.terraform.io/providers/hashicorp/google/6.46.0/docs/data-sources/project.
  google_infra_mgmt_project = {
    project_id = "infra-mgmt-${local.google_organization.org_id}"
  }

  _google_personal_principal = "john@${local.google_organization.domain}"

  # Mirrors the structure of the google_service_account data; see
  # https://registry.terraform.io/providers/hashicorp/google/6.46.0/docs/data-sources/service_account.
  google_personal_principal  = {
    email  = local._google_personal_principal
    member = "user:${local._google_personal_principal}"
  }

  # Mirrors the structure of the google_storage_bucket data; see
  # https://registry.terraform.io/providers/hashicorp/google/6.46.0/docs/data-sources/storage_bucket.
  infrastate_gcs_bucket = {
    name = "infrastate-${local.google_organization.org_id}"
  }

  # Mirrors the structure of the aws_s3_bucket data; see
  # https://registry.terraform.io/providers/hashicorp/aws/6.10.0/docs/data-sources/s3_bucket
  infrastate_s3_bucket = {
    bucket = "infrastate-${local.aws_organization.master_account_id}"
  }

  paths = {
    repo_root       = local.repo_root
    terragrunt_root = "${local.repo_root}/terragrunt"

    # This file is an AWS credentials file [1] of the form:
    #
    #   [terragrunt]
    #   aws_access_key_id=00000000000000000000
    #   aws_secret_access_key=0000000000000000000000000000000000000000
    #
    #   [management]
    #   aws_access_key_id=00000000000000000000
    #   aws_secret_access_key=0000000000000000000000000000000000000000
    #
    #
    # Other credential options should work, too, but long-term credential
    # is easiest to set up.
    #
    # The "management" credential should be an organization root user
    # credential *used only for bootstrapping*. Make sure to delete
    # it after bootstrapping is finished.
    #
    # [1]: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
    aws_credentials = "${local.terragrunt_credentials}/aws"

    # This file is a service account key [2] of the form:
    #
    #     {
    #         "type": "service_account",
    #         "project_id": "a-project-id",
    #         "private_key_id": "0000000000000000000000000000000000000000",
    #         "private_key": "-----BEGIN PRIVATE KEY-----\n[...]\n-----END PRIVATE KEY-----\n",
    #         "client_email": "terragrunt@a-project-id.iam.gserviceaccount.com",
    #         "client_id": "000000000000000000000",
    #         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    #         "token_uri": "https://oauth2.googleapis.com/token",
    #         "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    #         "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/terragrunt%40a-project-id.iam.gserviceaccount.com",
    #         "universe_domain": "googleapis.com"
    #     }
    google_credentials = "${local.terragrunt_credentials}/google.key"

    common_root = "${local.terragrunt_root}/common"

    # NOTE: the trailing slash here is important so that Terraform finds a "double-slash" at
    # the modules directory and interprets it as the module package. This allows for modules
    # to reference each other.
    #
    # See https://github.com/hashicorp/terraform/issues/23333#issuecomment-1261531854
    modules_root = "${local.terragrunt_root}/modules/"
  }

  # These variables are available to every unit via automatic generation.
  #
  # Modules can access them by using the "globals" module which is also
  # automatically generated.
  globals = {
     aws_organization          = local.aws_organization
     google_organization       = local.google_organization
     google_billing_account    = local.google_billing_account
     google_infra_mgmt_project = local.google_infra_mgmt_project
     google_personal_principal = local.google_personal_principal
     paths                     = local.paths
  }

  # Used in generated variable files (and the outputs of the globals module).
  global_descriptions = {
    aws_organization          = "the AWS organization that infrastructure is deployed to"
    google_organization       = "the GCP organization that infrastructure is deployed to"
    google_billing_account    = "the GCP billing account that infrastructure is billed to"
    google_infra_mgmt_project = "the GCP project used for infrastructure management"
    google_personal_principal = "the GCP principal used for day-to-day operations"
    paths                     = "paths to important resources under terragrunt's management"
  }

  global_vars_gen = { for k, v in local.globals: k => { description = lookup(local.global_descriptions, k), default = v } }
  global_outputs_gen = { for k, v in local.globals: k => { description = lookup(local.global_descriptions, k), value = v } }
}

remote_state {
  backend = "gcs"

  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }

  config = {
    bucket = local.infrastate_gcs_bucket.name
    prefix = "terragrunt/stacks/${replace(path_relative_to_include(), "/(.terragrunt-stack/|^stacks/[^/]+/)/", "")}"

    credentials = local.paths.google_credentials

    # We manage bucket bootstrapping ourselves.
    skip_bucket_creation = true
  }
}

################################
# Generated File Configuration #
################################

generate "provider" {
  path      = "provider.tf"
  if_exists = "skip"
  contents  = templatefile(
    "${local.paths.common_root}/provider.tf.tftpl",
    {
      aws_provider_profile        = "terragrunt"
      aws_provider_credentials    = local.paths.aws_credentials
      google_provider_credentials = local.paths.google_credentials
      globals                     = local.globals
    }
  )
}

generate "common_vars" {
  path      = "common_vars.tf"
  if_exists = "overwrite"
  contents  = file("${local.paths.common_root}/common_vars.tf")
}

#########################
# Globals Configuration #
#########################

generate "globals_module_vars" {
  path      = "${local.paths.modules_root}/globals/vars.tf.json"
  if_exists = "overwrite"
  contents  = jsonencode({ variable = local.global_vars_gen })

  # Required to prevent Terragrunt from including a comment and generating invalid JSON.
  disable_signature = true
}

generate "globals_module_outputs" {
  path      = "${local.paths.modules_root}/globals/outputs.tf.json"
  if_exists = "overwrite"
  contents  = jsonencode({ output = local.global_outputs_gen })

  # Required to prevent Terragrunt from including a comment and generating invalid JSON.
  disable_signature = true
}

generate "globals_unit_vars" {
  path      = "globals_vars.tf.json"
  if_exists = "overwrite"
  contents  = jsonencode({ variable = local.global_vars_gen })

  # Required to prevent Terragrunt from including a comment and generating invalid JSON.
  disable_signature = true
}
