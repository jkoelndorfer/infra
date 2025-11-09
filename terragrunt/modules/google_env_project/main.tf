module "g" {
  source = "../globals"
}

resource "random_string" "project_id_suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = false
  special = false
}

resource "google_project" "this" {
  name            = "${var.google_env_folder.env}-${var.function}"
  project_id      = "${var.google_env_folder.env}-${var.function}-${random_string.project_id_suffix.result}"
  folder_id       = var.google_env_folder.folder_id
  billing_account = module.g.google_billing_account.id

  labels = {
    function = var.function
  }
}

resource "google_project_service" "this" {
  for_each = toset(var.services)

  project = google_project.this.project_id
  service = each.value
}

# This resource ensures that google_project.this cannot be
# used before each google_project_service has been enabled.
resource "terraform_data" "after_project_service" {
  input = {
    apis = { for s in var.services : s => google_project_service.this[s].id }

    project = merge(
      google_project.this,
      {
        # Including this is necessary to prevent a Terraform bug from appearing.
        # On initial apply, Terraform errors:
        #
        #   │ Error: Provider produced inconsistent final plan
        #   │
        #   │ When expanding the plan for
        #   │ module.project.terraform_data.after_project_service to include new values
        #   │ learned so far during apply, provider "terraform.io/builtin/terraform"
        #   │ produced an invalid new value for .input.project.org_id: was null, but now
        #   │ cty.StringVal("").
        #   │
        #   │ This is a bug in the provider, which should be reported in the provider's
        #   │ own issue tracker.
        #
        org_id = module.g.google_organization.org_id
      }
    )
  }
}
