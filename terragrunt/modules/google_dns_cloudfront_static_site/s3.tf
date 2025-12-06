resource "aws_s3_bucket" "this" {
  bucket = "${data.aws_caller_identity.current.account_id}-site-${local.domain_slug}"
}

resource "aws_s3_bucket_ownership_controls" "enforce_bucket_owner" {
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "disallow_public" {
  bucket = aws_s3_bucket.this.id

  # Instead of a public bucket, use CloudFront's origin access control (OAC)
  # to provide access to the S3 bucket.
  #
  # https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
