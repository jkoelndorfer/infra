module "g" {
  source = "../globals"
}

# This secret is a simple dictionary.
#
# The key is a consistent name for the anonymous domain.
# The value is the domain name.
#
# The "//" key is reserved as a "comment".
data "google_secret_manager_secret_version_access" "anonymous_domains" {
  project = module.g.google_infra_mgmt_project.project_id

  secret = "anonymous-domains"
}

locals {
  anonymous_domains = jsondecode(data.google_secret_manager_secret_version_access.anonymous_domains.secret_data)
}
