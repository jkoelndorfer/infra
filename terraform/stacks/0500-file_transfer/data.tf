data "aws_route53_zone" "zone" {
  name         = local.env.zone
  private_zone = false
}

locals {
  domain_name = "files.${local.env.zone}"
}
