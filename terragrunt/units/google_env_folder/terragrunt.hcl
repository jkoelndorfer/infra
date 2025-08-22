include "root" {
  path   = find_in_parent_folders("root.hcl")
}

terraform {
  source = "./module"
}

inputs = merge(
  values,
  {
    google_env_folder = {
      name         = "not a real environment folder; use only env attribute"
      display_name = "not a real environment folder; use only env attribute"
      env          = values.env
      folder_id    = "000000000000"
    }
  }
)
