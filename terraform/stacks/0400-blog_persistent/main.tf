resource "aws_s3_bucket" "blog_bucket" {
  bucket = local.env["dns_zone"]
  acl    = "public-read"

  website {
    index_document = "index.html"
    error_document = "404.html"
  }
}
