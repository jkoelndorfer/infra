resource "aws_budgets_budget" "budget" {
  provider = aws.management

  name         = "Budget"
  budget_type  = "COST"
  limit_amount = var.aws_monthly_spend_limit_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator = "GREATER_THAN"
    threshold           = "100"
    threshold_type      = "PERCENTAGE"
    notification_type   = "FORECASTED"

    subscriber_email_addresses = [
      local.cloud_billing_alerts.notification_email,
      local.cloud_billing_alerts.google_chat_space.email,
    ]
  }

  notification {
    comparison_operator = "GREATER_THAN"
    threshold           = "100"
    threshold_type      = "PERCENTAGE"
    notification_type   = "ACTUAL"

    subscriber_email_addresses = [
      local.cloud_billing_alerts.notification_email,
      local.cloud_billing_alerts.google_chat_space.email,
    ]
  }

  notification {
    comparison_operator = "GREATER_THAN"
    threshold           = "200"
    threshold_type      = "PERCENTAGE"
    notification_type   = "ACTUAL"

    subscriber_email_addresses = [
      local.cloud_billing_alerts.notification_email,
      local.cloud_billing_alerts.google_chat_space.email,
    ]
  }
}
