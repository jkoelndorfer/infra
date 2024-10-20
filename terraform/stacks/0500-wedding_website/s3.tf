data "aws_iam_policy_document" "s3_cloudfront_access" {
  statement {
    sid     = "AllowCloudFrontRead"
    effect  = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "${data.terraform_remote_state.wedding_website_persistent.outputs.s3_bucket.arn}/*",
    ]
    principals {
      type        = "Service"
      identifiers = [
        "cloudfront.amazonaws.com",
      ]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [
        resource.aws_cloudfront_distribution.wedding_website.arn,
      ]
    }
  }
}

resource "aws_s3_bucket_website_configuration" "wedding_website" {
  bucket = data.terraform_remote_state.wedding_website_persistent.outputs.s3_bucket.bucket

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

resource "aws_s3_bucket_policy" "cloudfront_access" {
  bucket = data.terraform_remote_state.wedding_website_persistent.outputs.s3_bucket.bucket
  policy = data.aws_iam_policy_document.s3_cloudfront_access.json
}

resource "aws_s3_bucket_cors_configuration" "cors" {
  bucket = data.terraform_remote_state.wedding_website_persistent.outputs.s3_bucket.bucket

  cors_rule {
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
  }
}
