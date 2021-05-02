data "aws_iam_policy_document" "air_quality_access" {
  statement {
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = [local.env.put_metric_data_namespace]
    }
  }
}

resource "aws_iam_policy" "air_quality" {
  name        = "air-quality-${local.env.name}"
  description = "provides permissions for air quality actions in ${local.env.name}"
  policy      = data.aws_iam_policy_document.air_quality_access.json
}

resource "aws_iam_user" "air_quality" {
  name = "air-quality-${local.env.name}"
}

resource "aws_iam_user_policy_attachment" "air_quality" {
  user       = aws_iam_user.air_quality.name
  policy_arn = aws_iam_policy.air_quality.arn
}

resource "aws_iam_access_key" "air_quality" {
  user = aws_iam_user.air_quality.name
}
