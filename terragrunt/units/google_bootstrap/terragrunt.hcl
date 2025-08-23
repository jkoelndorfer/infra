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
    path = "${get_terragrunt_dir()}/../../google_bootstrap.tfstate"
  }
}

generate "google_bootstrap_default_provider" {
  path      = "google_default_provider.tf"
  if_exists = "overwrite"
  contents  = templatefile(
    "${include.root.locals.paths.common_root}/google_provider.tf.tftpl",
    {
      alias            = null
      billing_override = false
      credentials      = null
      globals          = include.root.locals.globals
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
      credentials      = null
      globals          = include.root.locals.globals
    }
  )
}

inputs = merge(
  values,
  {
    infrastate_gcs_bucket = include.root.locals.infrastate_gcs_bucket
  }
)
