module "vpc" {
  source = "../../modules/vpc/v1"

  category   = "core"
  cidr_block = local.env["vpc_cidr_block"]
  env        = local.env["name"]
  name       = "vpc0"
  ssh_port   = "22"
}
