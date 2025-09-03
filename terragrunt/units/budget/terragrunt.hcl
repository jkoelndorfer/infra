include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

terraform {
  source = "./module"
}

dependency "aws_infra_mgmt" {
  config_path = values.unit_paths.aws_infra_mgmt

  mock_outputs = values.aws_infra_mgmt
}

dependency "google_bootstrap" {
  config_path = values.unit_paths.google_bootstrap
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

generate "google_infra_provider" {
  path      = "google_infra_provider.tf"
  if_exists = "overwrite"
  contents  = templatefile(
    "${include.root.locals.paths.common_root}/google_provider.tf.tftpl",
    {
      alias            = "infra"
      billing_override = true
      credentials      = include.root.locals.paths.google_credentials
      globals          = include.root.locals.globals
    }
  )
}

inputs = merge(values, dependency.google_bootstrap.outputs)
