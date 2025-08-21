include "root" {
  path   = find_in_parent_folders("root.hcl")
}

terraform {
  source = "./module"
}

dependency "env_folder" {
  config_path = values.unit_paths.env_folder

  mock_outputs = values.mock_outputs.env_folder
}

inputs = merge(values, dependency.env_folder.outputs)
