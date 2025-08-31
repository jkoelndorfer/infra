locals {
  accounts = [
    {
      env      = "dev"
      function = "backup"
    },
    {
      env      = "prod"
      function = "backup"
    },
  ]

  accounts_map = { for a in local.accounts : "${a.env}-${a.function}" => a }
}

module "account" {
  for_each = local.accounts_map

  source = "${var.paths.modules_root}/aws_organizations_account"

  env       = each.value.env
  function  = each.value.function
  parent_id = local.ou_by_env[each.value.env].id
}
