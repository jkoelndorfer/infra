locals {
  s3_bucket = data.terraform_remote_state.blog_persistent.outputs.s3_bucket
  ssl_cert = data.terraform_remote_state.blog_persistent.outputs.ssl_cert

  blog_domain     = local.env.dns_zone
  blog_www_domain = "www.${local.env.dns_zone}"
}
