data "aws_iam_policy_document" "api_gw_logging_assume_role" {
  statement {
    sid     = "AllowAPIGatewayAssumeRoleLogging"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_gw_logging" {
  name = "prod-api-gateway-cloudwatch-logging"

  assume_role_policy = data.aws_iam_policy_document.api_gw_logging_assume_role.json
}

resource "aws_iam_role_policy_attachment" "api_gw_logging" {
  role       = aws_iam_role.api_gw_logging.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# API Gateway performs a check to make sure that the provided role has the correct
# permissions. This stack may need to be applied twice.
#
# This configuration lives in the "bootstrap" stack because this API Gateway resource
# is an account-wide setting.
resource "aws_api_gateway_account" "api_gw" {
  depends_on = [aws_iam_role_policy_attachment.api_gw_logging]

  cloudwatch_role_arn = aws_iam_role.api_gw_logging.arn
}
