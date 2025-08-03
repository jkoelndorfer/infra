include "root" {
  path   = find_in_parent_folders("root.hcl")
  expose = true
}

terraform {
  source = "./module"
}

inputs = merge(
  include.root.inputs,
  values,
)
