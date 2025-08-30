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
remote_state {
  backend = "local"

  generate = {
    path      = "backend.tf"
    if_exists = "overwrite"
  }

  config = {
    path = "${get_terragrunt_dir()}/../../aws_infra_mgmt.tfstate"
  }
}

dependency "aws_bootstrap" {
  config_path = values.unit_paths.aws_bootstrap

  mock_outputs = values.aws_bootstrap
}

generate "aws_infra_mgmt_provider" {
  path = "aws_infra_mgmt_provider.tf"
  if_exists = "overwrite"
  contents = templatefile(
    "${include.root.locals.paths.common_root}/aws_provider.tf.tftpl",
    {
      alias       = null
      region      = null
      assume_role = dependency.aws_bootstrap.outputs.aws_infra_mgmt_account.organization_access_role.arn
      profile     = "terragrunt"
      globals     = include.root.locals.globals
    }
  )
}

generate "aws_management" {
  path = "aws_management.tf"
  if_exists = "overwrite"
  contents = templatefile(
    "${include.root.locals.paths.common_root}/aws_provider.tf.tftpl",
    {
      alias       = "management"
      region      = null
      assume_role = null
      profile     = "management"
      globals     = include.root.locals.globals
    }
  )
}

inputs = merge(
  values,
  dependency.aws_bootstrap.outputs,
  {
    infrastate_s3_bucket = include.root.locals.infrastate_s3_bucket
  },
)
