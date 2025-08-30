resource "aws_iam_user" "personal" {
  name = var.aws_personal_principal.name
}

data "aws_iam_policy" "readonly" {
  name = "ReadOnlyAccess"
}

resource "aws_iam_user_policy_attachment" "personal_readonly" {
  user       = aws_iam_user.personal.name
  policy_arn = data.aws_iam_policy.readonly.arn
}

resource "aws_iam_user_policy_attachment" "personal_member_account_access" {
  user       = aws_iam_user.personal.name
  policy_arn = aws_iam_policy.organization_member_account_access.arn
}
