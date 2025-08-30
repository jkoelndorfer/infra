data "aws_iam_policy_document" "organization_member_account_access" {
  statement {
    sid    = "AllowOrganizationAssumeRole"
    effect = "Allow"

    actions = [
      "sts:AssumeRole",
    ]

    resources = [
      "arn:aws:iam::*:role/${var.aws_organization.member_account_access_role}",
    ]
  }
}

resource "aws_iam_policy" "organization_member_account_access" {
  name        = "OrganizationMemberAccountAccess"
  path        = "/"
  description = "Grants access to manage organization member accounts."
  policy      = data.aws_iam_policy_document.organization_member_account_access.json
}
