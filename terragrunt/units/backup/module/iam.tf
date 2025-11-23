locals {
  backup_ro_bucket_permissions = [
    "s3:GetBucketLocation",
    "s3:GetBucketVersioning",
    "s3:ListBucket",
    "s3:ListBucketMultipartUploads",
    "s3:ListBucketVersions",
  ]

  backup_ro_object_permissions = [
    "s3:GetObject",
    "s3:GetObjectAttributes",
    "s3:GetObjectRetention",
    "s3:GetObjectTagging",
    "s3:GetObjectVersion",
    "s3:GetObjectVersionTagging",
  ]

  backup_rw_object_permissions = concat(
    local.backup_ro_object_permissions,
    [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:DeleteObjectTagging",
      "s3:ListMultipartUploadParts",
      "s3:PutObject",
    ],
  )

  backup_deny_permissions = [
    "s3:DeleteObjectVersion",
    "s3:DeleteObjectVersionTagging",
    "s3:PutObjectVersionAcl",
    "s3:PutObjectVersionTagging",
  ]
}

data "aws_iam_policy_document" "home_backup" {
  statement {
    sid     = "AllowHomeBackupBucket"
    effect  = "Allow"
    actions = local.backup_ro_bucket_permissions
    resources = [
      aws_s3_bucket.backup.arn,
    ]
  }

  statement {
    sid     = "AllowHomeBackupObjects"
    effect  = "Allow"
    actions = local.backup_rw_object_permissions
    resources = [
      "${aws_s3_bucket.backup.arn}/archive/*",
      "${aws_s3_bucket.backup.arn}/syncthing/*",
      "${aws_s3_bucket.backup.arn}/photoprism/*",
      "${aws_s3_bucket.backup.arn}/restic/*",
    ]
  }

  statement {
    sid       = "DenyObjectVersionModification"
    effect    = "Deny"
    actions   = local.backup_deny_permissions
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "protect_backup_object_versions" {
  statement {
    sid       = "DenyObjectVersionModification"
    effect    = "Deny"
    actions   = local.backup_deny_permissions
    resources = ["*"]
  }
}

resource "aws_iam_policy" "home_backup" {
  name        = "HomeBackup"
  description = "Provides access for the homelab server to write to the backup bucket."
  policy      = data.aws_iam_policy_document.home_backup.json
}

resource "aws_iam_policy" "protect_backup_object_versions" {
  name        = "ProtectBackupObjectVersions"
  description = "Prevents deletion of previous bucket object versions."
  policy      = data.aws_iam_policy_document.protect_backup_object_versions.json
}

resource "aws_iam_role_policy_attachment" "protect_backup_object_versions" {
  role       = var.aws_organization.member_account_access_role
  policy_arn = aws_iam_policy.protect_backup_object_versions.arn
}
