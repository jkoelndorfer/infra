resource "aws_iam_policy" "lambda_logging" {
  name        = "${local.env.name}-lambda-logging"
  description = "Policy permitting Lambda to log to CloudWatch"
   policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:*",
      "Effect": "Allow"
    }
  ]
}
EOF
}
