locals {
  # Slightly obscured so that drive by bots don't pick up this email address. :-)
  budget_notifications_email = "cloud.spend@john.${var.google_organization.domain}"
}
