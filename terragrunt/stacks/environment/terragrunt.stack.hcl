locals {
  units_dir  = "${get_repo_root()}/terragrunt//units"
  unit_paths = {
    env_folder = "env_folder"
    dns        = "dns"
  }
  unit_paths_values = { for k, v in local.unit_paths: k => "../${v}" }

  common_values = {
    env        = values.env
    unit_paths = local.unit_paths_values

    mock_outputs = {
      env_folder = {
        env_folder = {
          env          = values.env
          display_name = "not a real environment folder; use only env attribute"
          name         = "not a real environment folder; use only env attribute"
          folder_id    = "000000000000"
        }
      }
    }
  }
}

unit "env_folder" {
  source = "${local.units_dir}/env_folder"
  path   = local.unit_paths.env_folder
  values = local.common_values
}

unit "dns" {
  source = "${local.units_dir}/dns"
  path   = local.unit_paths.dns
  values = local.common_values
}
