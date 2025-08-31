locals {
  identifier = var.env != "bootstrap" ? [var.env, var.function] : [var.function]
}

module "g" {
  source = "../globals"
}

resource "aws_organizations_account" "this" {
  email = templatestring(
    module.g.aws_organization.member_account_email_tmpl,
    {
      identifier                 = join(".", local.identifier)
      google_organization_domain = module.g.google_organization.domain
    }
  )
  name      = var.env != "bootstrap" ? join("-", local.identifier) : var.function
  role_name = module.g.aws_organization.member_account_access_role
  parent_id = var.parent_id

  close_on_deletion = true

  tags = {
    function = var.function
  }
}
