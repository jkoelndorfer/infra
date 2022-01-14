resource "aws_s3_bucket" "website_bucket" {
  bucket = "${local.aws_account_id}-website-${local.env.name}"
  acl    = "public-read"

  website {
    index_document = "index.html"
    error_document = "404.html"
  }
}

# This bucket contains additional assets deployed to the johnk.io website
# which are not committed to the website repository.
resource "aws_s3_bucket" "website_addl_assets_bucket" {
  bucket = "${local.aws_account_id}-website-addl-assets-${local.env.name}"
  acl    = "private"
}
