resource "aws_s3_bucket" "website_bucket" {
  bucket = "${local.aws_account_id}-website-${local.env.name}"
  acl    = "public-read"

  website {
    index_document = "index.html"
    error_document = "404.html"
  }
}
