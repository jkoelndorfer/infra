locals {
  unit_paths = {
    aws_accounts     = "aws_accounts"
    google_bootstrap = "google_bootstrap"
  }
  unit_paths_values = { for k, v in local.unit_paths: k => "../${v}" }
  bootstrap_values = {
    env = "prod"
    google_env_folder = {
      name         = "not a real environment folder; use only env attribute"
      display_name = "not a real environment folder; use only env attribute"
      env          = "prod"
      folder_id    = "000000000000"
    }
    unit_paths = local.unit_paths_values
  }
}

unit "aws_accounts" {
  source = "../..//units/aws_accounts"
  path   = local.unit_paths.aws_accounts
  values = local.bootstrap_values
}

unit "google_bootstrap" {
  source = "../..//units/google_bootstrap"
  path   = local.unit_paths.google_bootstrap
  values = local.bootstrap_values
}
