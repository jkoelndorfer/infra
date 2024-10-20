locals {
  s3_bucket = data.terraform_remote_state.wedding_website_persistent.outputs.s3_bucket
  ssl_cert  = data.terraform_remote_state.wedding_website_persistent.outputs.ssl_cert

  wedding_website_domain     = local.env.wedding_dns_zone
  wedding_website_www_domain = "www.${local.env.wedding_dns_zone}"
}
