resource "aws_s3_bucket" "blog_bucket" {
  bucket = "${local.aws_account_id}-blog-${local.env["name"]}"
  acl    = "public-read"

  website {
    index_document = "index.html"
    error_document = "404.html"
  }
}
