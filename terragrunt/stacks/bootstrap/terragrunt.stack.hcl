locals {
  bootstrap_values = {
    env = "prod"
    google_env_folder = {
      name         = "not a real environment folder; use only env attribute"
      display_name = "not a real environment folder; use only env attribute"
      env          = "prod"
      folder_id    = "000000000000"
    }
  }
}

unit "google_bootstrap" {
  source = "../..//units/google_bootstrap"
  path   = "google_bootstrap"
  values = local.bootstrap_values
}
