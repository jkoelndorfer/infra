include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

terraform {
  source = "./module"
}

# For more information on local backends using remote_state, see:
#   * https://github.com/gruntwork-io/terragrunt/issues/2179#issuecomment-1368307823
#   * https://stackoverflow.com/a/74977268
#   * https://terragrunt.gruntwork.io/docs/features/stacks/#configuration
#
#
# AWS accounts are tracked in local state to enable Terragrunt to access information
# about the accounts for provider generation purposes when units need to modify
# both dev and prod at the same time (e.g. production DNS zones delegating to a dev
# zone).
remote_state {
  backend = "local"

  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }

  config = {
    path = "${get_terragrunt_dir()}/../../aws_accounts.tfstate"
  }
}

generate "aws_organization_provider" {
  path = "aws_organization_provider.tf"
  if_exists = "overwrite"
  contents = templatefile(
    "${include.root.locals.paths.common_root}/aws_provider.tf.tftpl",
    {
      alias       = null
      region      = null
      assume_role = null
      profile     = "terragrunt"
      globals     = include.root.locals.globals
    }
  )
}

inputs = values
