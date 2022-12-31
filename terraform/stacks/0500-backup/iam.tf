locals {
  backup_bucket = data.terraform_remote_state.backup_persistent.outputs.s3_bucket.arn
  backup_ro_permissions = [
    "s3:GetBucketVersioning",
    "s3:GetObject",
    "s3:GetObjectAttributes",
    "s3:GetObjectRetention",
    "s3:GetObjectTagging",
    "s3:GetObjectVersion",
    "s3:GetObjectVersionTagging",
    "s3:ListBucket",
    "s3:ListBucketVersions",
  ]

  backup_rw_permissions = concat(
    local.backup_ro_permissions,
    [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:DeleteObjectTagging",
      "s3:ListBucketMultipartUploads",
      "s3:ListMultipartUploadParts",
      "s3:PutObject",
    ],
  )
}
resource "aws_iam_user" "backup_ro" {
  name = "backup-ro-${local.env.name}"
}

resource "aws_iam_access_key" "backup_ro" {
  user = aws_iam_user.backup_ro.name
}

resource "aws_ssm_parameter" "backup_ro_id" {
  name  = "/${local.env.name}/backup/creds/backup-ro/id"
  type  = "String"
  value = aws_iam_access_key.backup_ro.id
}

resource "aws_ssm_parameter" "backup_ro_secret" {
  name  = "/${local.env.name}/backup/creds/backup-ro/secret"
  type  = "SecureString"
  value = aws_iam_access_key.backup_ro.secret
}

data "aws_iam_policy_document" "backup_ro" {
  statement {
    sid     = "AllowBackupRead"
    effect  = "Allow"
    actions = local.backup_ro_permissions
    resources = [
      local.backup_bucket,
      "${local.backup_bucket}/*",
    ]
  }
}

resource "aws_iam_policy" "backup_ro" {
  name        = "backup-ro"
  description = "Provides read-only access to backup data in S3."
  policy      = data.aws_iam_policy_document.backup_ro.json
}

resource "aws_iam_user_policy_attachment" "backup_ro" {
  user       = aws_iam_user.backup_ro.name
  policy_arn = aws_iam_policy.backup_ro.arn
}

resource "aws_iam_user" "rclone" {
  name = "rclone-${local.env.name}"
}

resource "aws_iam_access_key" "rclone" {
  user = aws_iam_user.rclone.name
}

resource "aws_ssm_parameter" "rclone_id" {
  name  = "/${local.env.name}/backup/creds/rclone/id"
  type  = "String"
  value = aws_iam_access_key.rclone.id
}

resource "aws_ssm_parameter" "rclone_secret" {
  name  = "/${local.env.name}/backup/creds/rclone/secret"
  type  = "SecureString"
  value = aws_iam_access_key.rclone.secret
}

data "aws_iam_policy_document" "rclone" {
  statement {
    sid     = "AllowBackupReadWrite"
    effect  = "Allow"
    actions = local.backup_rw_permissions
    resources = [
      local.backup_bucket,
      "${local.backup_bucket}/syncthing/rclone/*",
    ]
  }

  statement {
    sid    = "AllowReadBackupParameters"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameterByPath",
      "ssm:GetParameters",
    ]
    resources = ["arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:parameter/${local.env.name}/backup/*"]
  }

  statement {
    sid    = "AllowSendBackupReport"
    effect = "Allow"
    actions = [
      "sns:Publish",
    ]
    resources = [data.terraform_remote_state.backup_persistent.outputs.sns_topic.arn]
  }
}

resource "aws_iam_policy" "rclone" {
  name        = "rclone"
  description = "Provides read-write access to rclone backup data in S3."
  policy      = data.aws_iam_policy_document.rclone.json
}

resource "aws_iam_user_policy_attachment" "rclone" {
  user       = aws_iam_user.rclone.name
  policy_arn = aws_iam_policy.rclone.arn
}
