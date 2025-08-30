data "aws_iam_policy_document" "infra_mgmt_organization_access" {
  statement {
    sid    = "AllowOrganizationManagement"
    effect = "Allow"

    actions = [
      "organizations:CloseAccount",
      "organizations:CreateAccount",
      "organizations:CreateOrganizationalUnit",
      "organizations:DescribeAccount",
      "organizations:DescribeCreateAccountStatus",
      "organizations:DescribeOrganization",
      "organizations:DescribeOrganizationalUnit",
      "organizations:ListAccounts",
      "organizations:ListAccountsForParent",
      "organizations:ListCreateAccountStatus",
      "organizations:ListOrganizationalUnitsForParent",
      "organizations:ListParents",
      "organizations:ListTagsForResource",
      "organizations:MoveAccount",
      "organizations:TagResource",
      "organizations:UntagResource",
      "organizations:UpdateOrganizationalUnit",
    ]

    resources = [
      "*",
    ]
  }
}

resource "aws_iam_policy" "infra_mgmt_organization_access" {
  name        = "InfrastructureManagementOrganizationAccess"
  path        = "/"
  description = "Grants access for infrastructure management tooling to manage the organization."
  policy      = data.aws_iam_policy_document.infra_mgmt_organization_access.json
}

resource "aws_iam_user" "terragrunt" {
  name = "terragrunt"
}

resource "aws_iam_user_policy_attachment" "terragrunt_infra_mgmt_organization_access" {
  user       = aws_iam_user.terragrunt.name
  policy_arn = aws_iam_policy.infra_mgmt_organization_access.arn
}

resource "aws_iam_user_policy_attachment" "terragrunt_organization_member_account_access" {
  user       = aws_iam_user.terragrunt.name
  policy_arn = aws_iam_policy.organization_member_account_access.arn
}
