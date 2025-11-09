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

# This secret contains information about how to send notifications for
# cloud billing alerts.
#
# When the Google Cloud Monitoring app is installed in a chat space,
# it prints this space ID in its initial message:
#
#     > Thanks for adding Google Cloud Monitoring app to your Google Chat
#     > space alerts (space id = xxxxxxxxxxx). Now you can use the space
#     > id to configure Google Chat notification channels in Google Cloud
#     > Monitoring
#
#
# This secret is a JSON blob of the form:
#
#     {
#       google_chat_space = {
#         id    = "$SPACE_ID",    # The Google Cloud Monitoring bot will provide this; see above.
#         email = "$SPACE_EMAIL"  # The email address that posts to this space.
#       },
#       notification_email = "email.address@example.com"  # A general notification email for billing alerts.
#     }
resource "google_secret_manager_secret" "google_chat_cloud_billing_alerts_space" {
  project = google_project.infra_mgmt.project_id

  secret_id = "cloud-billing-alerts"

  replication {
    auto {}
  }

  depends_on = [
    google_project_service.infra_mgmt,
  ]
}
