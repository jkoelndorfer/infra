include "root" {
  path   = find_in_parent_folders("root.hcl")
}

terraform {
  source = "./module"
}

dependency "google_env_folder" {
  config_path = values.unit_paths.google_env_folder

  mock_outputs = values.mock_outputs.google_env_folder
}

# This DNS unit delegates a subdomain of the "shared01"
# zone for homelab services. The homelab zone must be
# created before we can provision a record to
# delegate to it.
dependency "homelab_dns" {
  config_path = values.unit_paths.homelab_dns

  mock_outputs = values.mock_outputs.homelab_dns
}

inputs = merge(
  values,
  dependency.google_env_folder.outputs,
  dependency.homelab_dns.outputs,
)
