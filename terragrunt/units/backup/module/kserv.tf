resource "aws_iam_user" "kserv" {
  name = "kserv-backup"
}

resource "aws_iam_access_key" "kserv" {
  user = aws_iam_user.kserv.name
}

resource "aws_iam_user_policy_attachment" "kserv_backup" {
  user       = aws_iam_user.kserv.name
  policy_arn = aws_iam_policy.home_backup.arn
}

resource "kubernetes_secret_v1" "aws_backup" {
  metadata {
    namespace = module.namespace.name
    name      = "aws-backup"
  }

  data = {
    aws_access_key_id     = aws_iam_access_key.kserv.id
    aws_secret_access_key = aws_iam_access_key.kserv.secret
  }
}

# NOTE: The "restic" secret needs to be added to the backup namespace
# with a "repository_password" data. This ensures that the backup
# password isn't stored in the Terraform state file.
#
# $ kubectl -n prod-backup create secret generic restic
# $ kubectl -n prod-backup edit secret/restic
