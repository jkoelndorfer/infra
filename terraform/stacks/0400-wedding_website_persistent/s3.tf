resource "aws_s3_bucket" "wedding_website_bucket" {
  bucket = "${local.aws_account_id}-wedding-website-${local.env.name}"
}
