locals {
  s3_bucket = data.terraform_remote_state.website_persistent.outputs.s3_bucket
  ssl_cert = data.terraform_remote_state.website_persistent.outputs.ssl_cert

  website_domain     = local.env.dns_zone
  website_www_domain = "www.${local.env.dns_zone}"
}
