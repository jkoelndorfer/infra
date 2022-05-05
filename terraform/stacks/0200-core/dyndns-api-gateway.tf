resource "aws_lambda_function_url" "dyndns" {
  authorization_type = "NONE"
  function_name      = aws_lambda_function.dyndns.function_name
}

resource "aws_ssm_parameter" "api_gateway_dyndns_url" {
  name        = "/${local.env.name}/dyndns/url"
  type        = "String"
  value       = aws_lambda_function_url.dyndns.function_url
  description = "URL providing dynamic DNS functionality in ${local.env.name}."
}
