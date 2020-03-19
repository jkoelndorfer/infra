resource "aws_api_gateway_rest_api" "dyndns_api" {
  name        = "${local.env["name"]}-dyndns"
  description = "API for client-initiated DNS in ${local.env["name"]}."

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "update" {
  rest_api_id = aws_api_gateway_rest_api.dyndns_api.id
  parent_id   = aws_api_gateway_rest_api.dyndns_api.root_resource_id
  path_part   = "update"
}

resource "aws_api_gateway_method" "update" {
  rest_api_id   = aws_api_gateway_rest_api.dyndns_api.id
  resource_id   = aws_api_gateway_resource.update.id
  http_method   = "POST"
  authorization = "NONE"  # the dynamic DNS Lambda function does its own authorization
}

resource "aws_api_gateway_integration" "update" {
  rest_api_id = aws_api_gateway_rest_api.dyndns_api.id
  resource_id = aws_api_gateway_resource.update.id
  http_method = aws_api_gateway_method.update.http_method
  type        = "AWS_PROXY"
  uri         = aws_lambda_function.dyndns.invoke_arn

  integration_http_method = "POST"
}

resource "aws_api_gateway_deployment" "dyndns" {
  depends_on  = [aws_api_gateway_integration.update]
  rest_api_id = aws_api_gateway_rest_api.dyndns_api.id
}

resource "aws_api_gateway_stage" "dyndns" {
  rest_api_id   = aws_api_gateway_rest_api.dyndns_api.id
  stage_name    = local.env["name"]
  deployment_id = aws_api_gateway_deployment.dyndns.id
}

resource "aws_api_gateway_method_settings" "update" {
  rest_api_id   = aws_api_gateway_rest_api.dyndns_api.id
  stage_name    = aws_api_gateway_stage.dyndns.stage_name
  method_path   = "${aws_api_gateway_resource.update.path_part}/${aws_api_gateway_method.update.http_method}"

  settings {
    logging_level          = "INFO"
    throttling_rate_limit  = 100
    throttling_burst_limit = 100
  }
}

locals {
  rest_api_source_arn_resource = "${aws_api_gateway_rest_api.dyndns_api.id}/*/${aws_api_gateway_method.update.http_method}${aws_api_gateway_resource.update.path}"
}

resource "aws_lambda_permission" "api_gateway_dyndns_lambda_invocation" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dyndns.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${local.env["default_aws_region"]}:${data.aws_caller_identity.current.account_id}:${local.rest_api_source_arn_resource}"
}
