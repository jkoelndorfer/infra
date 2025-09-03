variable "aws_monthly_spend_limit_usd" {
  type        = number
  description = "the spend limit for AWS in USD"
  default     = 10
}

variable "gcp_monthly_spend_limit_usd" {
  type        = number
  description = "the spend limit for GCP in USD"
  default     = 5
}
