resource "aws_iam_user" "miniserv" {
  name = "miniserv-backup"
}

resource "aws_iam_access_key" "miniserv" {
  user = aws_iam_user.miniserv.name
}

resource "aws_iam_user_policy_attachment" "miniserv_backup" {
  user       = aws_iam_user.miniserv.name
  policy_arn = aws_iam_policy.home_backup.arn
}
