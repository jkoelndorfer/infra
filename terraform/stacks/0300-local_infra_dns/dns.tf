locals {
  dyndns_hostname = data.terraform_remote_state.core.outputs.dyndns_hostname
}

data "aws_route53_zone" "zone" {
  name         = local.env.dns_zone
  private_zone = false
}

resource "aws_route53_record" "records" {
  for_each = toset(local.env.home_cname_records)

  zone_id = data.aws_route53_zone.zone.zone_id
  name    = "${each.value}.${local.env.dns_zone}"
  type    = "CNAME"
  ttl     = 300
  records = [local.dyndns_hostname]
}
