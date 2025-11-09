output "miniserv_iam" {
  description = "IAM credentials used by miniserv to perform backups"
  value = {
    user = {
      arn  = aws_iam_user.miniserv.arn
      name = aws_iam_user.miniserv.name
    }
    access_key = {
      id     = aws_iam_access_key.miniserv.id
      secret = aws_iam_access_key.miniserv.secret
    }
  }
  sensitive = true
}
