locals {
  s3_origin = "s3-${local.domain_slug}"
}

resource "aws_cloudfront_origin_access_control" "this" {
  name             = local.domain_slug
  description      = "Permits CloudFront to access the ${local.domain} hosting bucket."
  signing_behavior = "always"
  signing_protocol = "sigv4"

  origin_access_control_origin_type = "s3"
}

resource "aws_cloudfront_cache_policy" "cors_origin" {
  name    = "${local.domain_slug}-cors"
  comment = "policy for caching based on CORS origin"

  min_ttl     = 0
  default_ttl = (60 * 60)
  max_ttl     = (60 * 60 * 24)

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
      cookies {
        items = []
      }
    }

    headers_config {
      header_behavior = "whitelist"

      headers {
        items = ["Origin"]
      }
    }

    query_strings_config {
      query_string_behavior = "none"
      query_strings {
        items = []
      }
    }
  }
}

resource "aws_cloudfront_distribution" "this" {
  origin {
    domain_name              = aws_s3_bucket.this.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.this.id
    origin_id                = local.s3_origin
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  aliases = [local.domain, "www.${local.domain}"]

  custom_error_response {
    error_caching_min_ttl = 60
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
  }

  default_cache_behavior {
    allowed_methods  = ["HEAD", "GET", "OPTIONS"]
    cached_methods   = ["HEAD", "GET", "OPTIONS"]
    target_origin_id = local.s3_origin
    cache_policy_id  = aws_cloudfront_cache_policy.cors_origin.id

    viewer_protocol_policy = "redirect-to-https"
  }

  ordered_cache_behavior {
    path_pattern     = "/fonts/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = local.s3_origin
    cache_policy_id  = aws_cloudfront_cache_policy.cors_origin.id

    min_ttl     = 3600
    default_ttl = 604800
    max_ttl     = 604800

    viewer_protocol_policy = "redirect-to-https"
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.this.arn
    ssl_support_method  = "sni-only"
  }
}
