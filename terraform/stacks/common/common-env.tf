data "aws_caller_identity" "current" {}

locals {
  aws_account_id = data.aws_caller_identity.current.account_id

  environments_globals_defaults = {
    default_ec2_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCpfRhcMcO9/7PN6USiFh6zJePFi31rdBI+hHNhy6/2WrjGnHp/kOLIRbv4TIpX+XVoseoEb3tcLaPm2YQLmrVl53MAqmXwmFPryKZMIzttoDtXw9V/tXCOFEuPv5YK3wPbXruPLB2gHQgB+denUDS8qSQ9s08K/jqR2v04kOFaDyfuL1dJo0OB6lGRsZV0a/lcNZLG3AaRvsRDVFSUWj1z5ACR4tSHcKwJnq+NsS1vuzTaQpc40WZPvJrNHNSQywHAELvLszIdLfKUBpFX4YLk4zk9+46GkeclIY3dqXtwz+NEw2OWJIUDgPHzQB1m9NZbUzNfpPvAEdyJ5EX6GszR"
    default_aws_region     = "us-east-1"
    backup_subnet_num      = "1"
  }
  environments_globals = {
    dev = {
      name           = "dev"
      dns_zone       = "dev.johnk.io"
      vpc_cidr_block = "10.99.0.0/16"
    }
    prod = {
      name           = "prod"
      dns_zone       = "johnk.io"
      vpc_cidr_block = "10.100.0.0/16"
    }
  }

  env = merge(
    local.environments_globals_defaults,
    local.environments_globals[terraform.workspace],
    local.environments[terraform.workspace],
  )
}

output "env" {
  description = "environment we are operating in, e.g. dev or prod"
  value       = local.env["name"]
}
