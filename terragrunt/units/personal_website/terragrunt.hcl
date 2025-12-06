include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

terraform {
  source = "./module"
}

dependency "dns" {
  config_path = values.unit_paths.dns

  mock_outputs = values.mock_outputs.dns
}

inputs = merge(
  values,
  dependency.dns.outputs,
)

