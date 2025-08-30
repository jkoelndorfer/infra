data "aws_iam_policy_document" "terragrunt_org_infrastructure_state_assume" {
  provider = aws.management

  statement {
    sid    = "AllowAssumingInfrastructureStateUpdater"
    effect = "Allow"

    actions = [
      "sts:AssumeRole",
    ]

    resources = [
      aws_iam_role.infrastructure_state_updater.arn,
    ]
  }
}

resource "aws_iam_policy" "terragrunt_org_infrastructure_state_assume" {
  provider = aws.management

  name   = "InfrastructureStateUpdateAssumer"
  policy = data.aws_iam_policy_document.terragrunt_org_infrastructure_state_assume.json
}

resource "aws_iam_user_policy_attachment" "terragrunt_org_infrastructure_state_assume" {
  provider = aws.management

  user       = var.terragrunt_user.name
  policy_arn = aws_iam_policy.terragrunt_org_infrastructure_state_assume.arn
}
