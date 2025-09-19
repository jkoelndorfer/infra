include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

terraform {
  source = "./module"
}

dependency "google_env_folder" {
  config_path = values.unit_paths.google_env_folder

  mock_outputs = values.mock_outputs.google_env_folder
}

inputs = merge(
  values,
  dependency.google_env_folder.outputs,
)
