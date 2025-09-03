resource "google_monitoring_notification_channel" "budget_email" {
  project = var.google_infra_mgmt_project.project_id

  display_name = "Budget Email"
  type         = "email"

  labels = {
    email_address = local.cloud_billing_alerts.notification_email
  }
}

resource "google_monitoring_notification_channel" "budget_chat_space" {
  project = var.google_infra_mgmt_project.project_id

  # It seems that budget alerts do not support Google Chat notification
  # channels. When I try to provision one, I receive the error:
  #
  #
  #   googleapi: Error 400: Request contains an invalid argument.
  #
  #
  # So let's just use an email for now.
  display_name = "Budget Chat Space"
  type         = "email"

  labels = {
    email_address = local.cloud_billing_alerts.google_chat_space.email
  }
}

resource "google_billing_budget" "budget" {
  provider = google.infra

  billing_account = var.google_billing_account.id
  display_name    = "Budget"

  budget_filter {
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = var.gcp_monthly_spend_limit_usd
    }
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "FORECASTED_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 2.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    monitoring_notification_channels = [
      google_monitoring_notification_channel.budget_email.id,
      google_monitoring_notification_channel.budget_chat_space.id,
    ]

    disable_default_iam_recipients = true
  }
}
