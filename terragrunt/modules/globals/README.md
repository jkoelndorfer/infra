Global Variable Module
======================

This module exists so that other modules in this repository can use global
values, such as the GCP organization ID, without having to always pass in
that information.

This module is entirely auto-generated using
[JSON configuration syntax](https://developer.hashicorp.com/terraform/language/v1.11.x/syntax/json)
to ensure that variables are properly encoded.

This module provisions no resources and performs no lookups. It only provides
access to global values from Terragrunt's `root.hcl`.

When to Use
-----------

Use this module only within other **modules**. Units have access to these globals
directly via variables.

Example
-------

```terraform
module "g" {
  source = "../globals"
}

resource "google_project" "example" {
  name       = "My Example Project"
  project_id = "my-example-project"
  org_id     = module.g.gcp_organization.org_id
}
```
