include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

terraform {
  source = "./module"
}

inputs = merge(
  values,
  values.mock_outputs.google_env_folder,
)

