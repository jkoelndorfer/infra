include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

terraform {
  source = "./module"
}

dependency "homelab_dns" {
  config_path = values.unit_paths.homelab_dns

  mock_outputs = values.mock_outputs.homelab_dns
}

dependency "homelab_traefik" {
  config_path = values.unit_paths.homelab_traefik

  mock_outputs = values.mock_outputs.homelab_traefik
}

inputs = merge(
  values,
  values.mock_outputs.google_env_folder,
  dependency.homelab_dns.outputs,
)
