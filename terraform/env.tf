locals {
  amazon_marketplace_id = "679593333241"
  environment_defaults = {
    default_ec2_public_key= "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCpfRhcMcO9/7PN6USiFh6zJePFi31rdBI+hHNhy6/2WrjGnHp/kOLIRbv4TIpX+XVoseoEb3tcLaPm2YQLmrVl53MAqmXwmFPryKZMIzttoDtXw9V/tXCOFEuPv5YK3wPbXruPLB2gHQgB+denUDS8qSQ9s08K/jqR2v04kOFaDyfuL1dJo0OB6lGRsZV0a/lcNZLG3AaRvsRDVFSUWj1z5ACR4tSHcKwJnq+NsS1vuzTaQpc40WZPvJrNHNSQywHAELvLszIdLfKUBpFX4YLk4zk9+46GkeclIY3dqXtwz+NEw2OWJIUDgPHzQB1m9NZbUzNfpPvAEdyJ5EX6GszR"
    default_aws_region = "us-east-1"
    backup_subnet_num = "1"
  }
  environments = {
    dev = {
      name = "dev"
      dns_zone = "dev.johnk.io"
      vpc_cidr_block = "10.99.0.0/16"
      syncthing_ami = "syncthing 2019-03-01 2201"
    }
    prod = {
      name = "prod"
      dns_zone = "johnk.io"
      vpc_cidr_block = "10.100.0.0/16"
      syncthing_ami = "syncthing 2019-03-02 1534"
    }
  }
  env = "${merge(local.environment_defaults, local.environments[terraform.workspace])}"
}

output "env" {
  description = "environment we are operating in, e.g. dev or prod"
  value = "${local.env["name"]}"
}
