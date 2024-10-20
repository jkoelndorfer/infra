output "rsvp_url" {
  description = "URL for RSVP Lambda function"
  value       = aws_lambda_function_url.rsvp.function_url
}
