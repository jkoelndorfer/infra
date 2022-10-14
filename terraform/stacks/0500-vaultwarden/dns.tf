locals {
  dyndns_hostname = data.terraform_remote_state.core.outputs.dyndns_hostname
}

data "aws_route53_zone" "zone" {
  name         = local.env.zone
  private_zone = false
}

resource "aws_route53_record" "vaultwarden" {
  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "vaultwarden.${local.env.zone}"
  type    = "CNAME"
  ttl     = 300
  records = [local.dyndns_hostname]
}
