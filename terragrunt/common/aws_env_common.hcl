locals {
  aws_accounts_tfstate_path = "../stacks/bootstrap/aws_accounts.tfstate"
  aws_accounts_tfstate = jsondecode(file(local.aws_accounts_tfstate_path))

  aws_accounts = local.aws_accounts_tfstate.outputs.accounts.value
}
