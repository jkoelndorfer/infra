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
    path = "${get_terragrunt_dir()}/../../aws_accounts.tfstate"
  }
}

generate "provider_bootstrap" {
  path      = "provider.tf"
  if_exists = "overwrite"
  contents  = templatefile(
    "${include.root.locals.paths.terragrunt_root}/common/provider.tf.tftpl",
    {
      aws_provider_profile        = "management"
      aws_provider_credentials    = include.root.locals.paths.aws_credentials
      google_provider_credentials = ""
      globals                     = include.root.locals.globals
    }
  )
}

inputs = {
  env = values.env
  google_env_folder = {
    env          = values.env
    display_name = "not a real environment folder; use only env attribute"
    name         = "not a real environment folder; use only env attribute"
    folder_id    = "000000000000"
  }
  infrastate_s3_bucket = include.root.locals.infrastate_s3_bucket
}
