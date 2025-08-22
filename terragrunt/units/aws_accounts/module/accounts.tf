locals {
  accounts = {
    infra_mgmt = {
      env      = "bootstrap"
      function = "infra-mgmt"
    }
  }
}

module "aws_account" {
  for_each = local.accounts

  source = "${var.paths.modules_root}/aws_organizations_account"

  env      = each.value.env
  function = each.value.function
}
