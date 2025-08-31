resource "aws_organizations_organizational_unit" "dev" {
  name      = "dev"
  parent_id = var.aws_organization.root_ou.id
}

resource "aws_organizations_organizational_unit" "prod" {
  name      = "prod"
  parent_id = var.aws_organization.root_ou.id
}

locals {
  ou_by_env = {
    dev  = aws_organizations_organizational_unit.dev
    prod = aws_organizations_organizational_unit.prod
  }
}
