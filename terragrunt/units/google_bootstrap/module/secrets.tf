# This secret contains a list of "anonymous domains". These
# domains aren't listed here because they're meant to be
# slightly more private than one which is my literal name.
#
# One reason for anonymity is to provide similar functionality
# to Fastmail's masked email feature. [1] The domain(s) would
# be configured as "catch-all" for delivery purposes, so
# avoiding unwanted advertising is nice.
#
# Once this secret is created, populate it with a JSON
# dictionary where each key is an identifier for the domain
# and the value is the root zone. The identifier is intended
# to be public. An example secret value would be:
#
#
#     {
#         "mail": "my-email.com",
#         "homelab": "home-lab-stuff.net"
#     }
#
#
# [1]: https://www.fastmail.com/features/masked-email/
resource "google_secret_manager_secret" "anonymous_domains" {
  project = google_project.infra_mgmt.project_id

  secret_id = "anonymous-domains"

  replication {
    auto {}
  }

  depends_on = [
    google_project_service.infra_mgmt,
  ]
}
