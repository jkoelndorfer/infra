data "aws_iam_policy_document" "cloudwatch_assume_role" {
  statement {
    sid     = "AllowCloudWatchEventServiceAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cloudwatch_dyndns" {
  name = "${local.env["name"]}-cloudwatch-dyndns"

  assume_role_policy = data.aws_iam_policy_document.cloudwatch_assume_role.json
}

data "aws_iam_policy_document" "cloudwatch_dyndns" {
  statement {
    sid       = "AllowCloudWatchEventServiceInvokeLambda"
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.dyndns.arn]
  }
}

resource "aws_iam_policy" "cloudwatch_dyndns" {
  name        = "${local.env["name"]}-cloudwatch-dyndns"
  description = "Policy permitting CloudWatch to invoke the dynamic DNS Lambda function"
  policy      = data.aws_iam_policy_document.cloudwatch_dyndns.json
}


resource "aws_iam_role_policy_attachment" "cloudwatch_dyndns" {
  role       = aws_iam_role.cloudwatch_dyndns.name
  policy_arn = aws_iam_policy.cloudwatch_dyndns.arn
}

resource "aws_cloudwatch_event_rule" "ec2_instance_running" {
  name        = "${local.env["name"]}-dyndns-ec2-instance-running"
  description = "Fires when an event at the dyndns Lambda function when an EC2 instance enters the running state"
  role_arn    = aws_iam_role.cloudwatch_dyndns.arn
  event_pattern = jsonencode({
      source      = ["aws.ec2"],
      detail-type = ["EC2 Instance State-change Notification"],
      detail = {
        state = ["running"]
      }
  })
}

resource "aws_cloudwatch_event_target" "dyndns" {
  target_id = "${local.env["name"]}-ec2state-dyndns"
  rule      = aws_cloudwatch_event_rule.ec2_instance_running.name
  arn       = aws_lambda_function.dyndns.arn
}

resource "aws_lambda_permission" "cloudwatch_dyndns" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dyndns.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ec2_instance_running.arn
}
