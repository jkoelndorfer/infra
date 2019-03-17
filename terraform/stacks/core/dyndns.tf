resource "aws_iam_role" "dyndns" {
  name = "${local.env["name"]}-lambda-dyndns"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "dyndns" {
  name        = "${local.env["name"]}-lambda-dyndns"
  description = "Policy permitting Lambda to perform actions needed for cloud dynamic DNS"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeTags"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Action": [
        "route53:ListHostedZones",
        "route53:ChangeResourceRecordSets"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "dyndns" {
  role       = "${aws_iam_role.dyndns.name}"
  policy_arn = "${aws_iam_policy.dyndns.arn}"
}

resource "aws_iam_role_policy_attachment" "dyndns_logging" {
  role       = "${aws_iam_role.dyndns.name}"
  policy_arn = "${aws_iam_policy.lambda_logging.arn}"
}

# TODO: Create a Lambda module that automatically handles logging
# and necessary permissions.

resource "aws_lambda_function" "dyndns" {
  # This is a dummy package so we can deploy the Lambda function.
  # Apply updates from the "cloud-tools" repository.
  filename      = "dyndns.zip"
  function_name = "${local.env["name"]}-dyndns"
  handler       = "dyndns.lambda_handler"
  role          = "${aws_iam_role.dyndns.arn}"
  description   = "Provides dynamic DNS as EC2 instances come online."
  memory_size   = 128
  runtime       = "python3.7"
  timeout       = 5
  environment {
    variables = {
      "env_name" = "${local.env["name"]}"
    }
  }
  tags {
    "johnk:category" = "core"
    "johnk:env"      = "${local.env["name"]}"
  }
}

resource "aws_iam_role" "cloudwatch_dyndns" {
  name = "${local.env["name"]}-cloudwatch-dyndns"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "cloudwatch_dyndns" {
  name        = "${local.env["name"]}-cloudwatch-dyndns"
  description = "Policy permitting CloudWatch to invoke the dynamic DNS Lambda function"
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "lambda:InvokeFunction",
      "Effect": "Allow",
      "Resource": "${aws_lambda_function.dyndns.arn}"
    }
  ]
}
EOF
}


resource "aws_iam_role_policy_attachment" "cloudwatch_dyndns" {
  role       = "${aws_iam_role.cloudwatch_dyndns.name}"
  policy_arn = "${aws_iam_policy.cloudwatch_dyndns.arn}"
}

resource "aws_cloudwatch_event_rule" "ec2_instance_running" {
  name        = "${local.env["name"]}-dyndns-ec2-instance-running"
  description = "Fires when an event at the dyndns Lambda function when an EC2 instance enters the running state"
  role_arn    = "${aws_iam_role.cloudwatch_dyndns.arn}"
  event_pattern = <<EOF
    {
      "source": ["aws.ec2"],
      "detail-type": ["EC2 Instance State-change Notification"],
      "detail": {
        "state": ["running"]
      }
    }
EOF
}

resource "aws_cloudwatch_event_target" "dyndns" {
  target_id = "${local.env["name"]}-ec2state-dyndns"
  rule      = "${aws_cloudwatch_event_rule.ec2_instance_running.name}"
  arn       = "${aws_lambda_function.dyndns.arn}"
}

resource "aws_lambda_permission" "cloudwatch_dyndns" {
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.dyndns.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.ec2_instance_running.arn}"
}
