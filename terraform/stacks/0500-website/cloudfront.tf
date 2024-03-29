locals {
  origin_id = "website-${local.env.name}"
}

resource "aws_cloudfront_distribution" "this" {
  origin {
    domain_name = local.s3_bucket.bucket_regional_domain_name
    origin_id   = local.origin_id
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  aliases = [local.website_domain, local.website_www_domain]

  custom_error_response {
    error_caching_min_ttl = 60
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
  }

  default_cache_behavior {
    allowed_methods  = ["HEAD", "GET", "OPTIONS"]
    cached_methods   = ["HEAD", "GET", "OPTIONS"]
    target_origin_id = local.origin_id

    min_ttl     = 0
    default_ttl = 600
    max_ttl     = 1800

    forwarded_values {
      cookies {
        forward = "none"
      }
      headers      = []
      query_string = false
    }

    viewer_protocol_policy = "redirect-to-https"
  }

  ordered_cache_behavior {
    path_pattern     = "/fonts/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = local.origin_id

    min_ttl     = 3600
    default_ttl = 604800
    max_ttl     = 604800

    forwarded_values {
      cookies {
        forward = "none"
      }
      headers      = []
      query_string = false
    }

    viewer_protocol_policy = "redirect-to-https"
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn = local.ssl_cert.arn
    ssl_support_method  = "sni-only"
  }
}
