locals {
  gcp_organization_id    = "285001668841"
  gcp_billing_account_id = "018603-0A0108-775C8E"

  tfstate_gcs_bucket  = "${local.gcp_organization_id}-tfstate"
}

remote_state {
  backend = "gcs"

  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }

  config = {
    bucket = local.tfstate_gcs_bucket
    prefix = "${path_relative_to_include()}/tofu.tfstate"

    # We manage bucket bootstrapping ourselves.
    skip_bucket_creation = true
  }

  disable_init = true
}

################################
# Generated File Configuration #
################################

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite"
  contents  = file("common/provider.tf")
}

generate "common_vars" {
  path      = "common_vars.tf"
  if_exists = "overwrite"
  contents  = file("common/common_vars.tf")
}

#################
# Common Inputs #
#################
inputs = {
  gcp_organization_id    = local.gcp_organization_id
  gcp_billing_account_id = local.gcp_billing_account_id
}
