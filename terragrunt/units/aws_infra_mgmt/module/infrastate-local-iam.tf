# Policy that denies the ability to modify previous object versions.
# This is a safeguard to protect against glitches or accidents while
# running Terraform.
data "aws_iam_policy_document" "infrastructure_state_updater" {
  statement {
    sid    = "AllowListBucket"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.infrastate.arn,
    ]
  }

  statement {
    sid    = "AllowBucketCurrentObjectModification"
    effect = "Allow"

    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject",
    ]

    resources = [
      "${aws_s3_bucket.infrastate.arn}/*",
    ]
  }

  statement {
    sid    = "DenyBucketObjectVersionModification"
    effect = "Deny"

    actions = [
      "s3:DeleteObjectVersion",
      "s3:DeleteObjectVersionTagging",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionAcl",
      "s3:GetObjectVersionAttributes",
      "s3:GetObjectVersionForReplication",
      "s3:GetObjectVersionTagging",
      "s3:GetObjectVersionTorrent",
      "s3:PutObjectVersionAcl",
      "s3:PutObjectVersionTagging",
    ]

    resources = [
      "*",
    ]
  }
}

data "aws_iam_policy_document" "infrastructure_state_updater_assume_role_policy" {
  statement {
    sid    = "AssumeRole"
    effect = "Allow"

    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "AWS"
      identifiers = [
        var.terragrunt_user.arn,
      ]
    }
  }
}

resource "aws_iam_policy" "infrastructure_state_updater" {
  name   = "InfrastructureStateUpdater"
  policy = data.aws_iam_policy_document.infrastructure_state_updater.json
}

resource "aws_iam_role" "infrastructure_state_updater" {
  name = "InfrastructureStateUpdater"

  assume_role_policy = data.aws_iam_policy_document.infrastructure_state_updater_assume_role_policy.json
}

resource "aws_iam_role_policy_attachment" "terragrunt_infrastructure_state_updater" {
  role       = aws_iam_role.infrastructure_state_updater.name
  policy_arn = aws_iam_policy.infrastructure_state_updater.arn
}
