module "infra_mgmt_account" {
  source = "${var.paths.modules_root}/aws_organizations_account"

  env      = "bootstrap"
  function = "infra-mgmt"
}
