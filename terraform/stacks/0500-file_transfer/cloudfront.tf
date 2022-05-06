locals {
  s3_origin_id = "s3"
}

resource "aws_cloudfront_distribution" "file_transfer" {
  origin {
    domain_name = aws_s3_bucket.file_transfer.bucket_regional_domain_name
    origin_id   = local.s3_origin_id
  }

  enabled         = true
  is_ipv6_enabled = true
  comment         = "file-transfer-${local.env.name}"

  aliases = [local.domain_name]

  default_cache_behavior {
    target_origin_id = local.s3_origin_id

    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods  = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"

    min_ttl     = 0
    default_ttl = 600
    max_ttl     = 3600
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn = module.cert.acm_certificate_arn
    ssl_support_method  = "sni-only"
  }
}
