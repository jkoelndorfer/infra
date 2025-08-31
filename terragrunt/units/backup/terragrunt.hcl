locals {
  unit_name = "backup"
}

include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

include "aws_env_common" {
  path   = "${find_in_parent_folders("common")}/aws_env_common.hcl"
  expose = true
}

terraform {
  source = "./module"
}

dependency "google_env_folder" {
  config_path = values.unit_paths.google_env_folder

  mock_outputs = values.mock_outputs.google_env_folder
}

generate "aws_provider" {
  path      = "aws_provider.tf"
  if_exists = "overwrite"

  contents = templatefile(
    "${include.root.locals.paths.common_root}/aws_provider.tf.tftpl",
    {
      alias       = null
      region      = null
      assume_role = include.aws_env_common.locals.aws_accounts["${values.env}-${local.unit_name}"].organization_access_role.arn
      profile     = "terragrunt"
      globals     = include.root.locals.globals
    }
  )
}

inputs = merge(
  values,
  dependency.google_env_folder.outputs
)
