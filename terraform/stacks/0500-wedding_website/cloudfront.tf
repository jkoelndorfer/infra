locals {
  origin_id = "wedding-website-${local.env.name}"
}

resource "aws_cloudfront_origin_access_control" "oac" {
  name             = "cloudfront-wedding-${local.env.name}"
  description      = "Permits CloudFront to access the ${local.env.name} wedding website bucket."
  signing_behavior = "always"
  signing_protocol = "sigv4"

  origin_access_control_origin_type = "s3"
}


resource "aws_cloudfront_cache_policy" "wedding_cors" {
  name        = "wedding-cors-${local.env.name}"
  comment     = "policy for caching based on CORS Origin"
  min_ttl     = 0
  default_ttl = 600
  max_ttl     = 1800

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

resource "aws_route53_record" "wedding_website_www" {
  zone_id = data.aws_route53_zone.cert_zone.zone_id
  name    = "www.${data.aws_route53_zone.cert_zone.name}"
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.wedding_website.domain_name
    zone_id                = aws_cloudfront_distribution.wedding_website.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_cloudfront_distribution" "wedding_website" {
  origin {
    domain_name              = local.s3_bucket.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
    origin_id                = local.origin_id
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  aliases = [local.wedding_website_domain, local.wedding_website_www_domain]

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
    cache_policy_id  = aws_cloudfront_cache_policy.wedding_cors.id

    viewer_protocol_policy = "redirect-to-https"
  }

  ordered_cache_behavior {
    path_pattern     = "/fonts/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = local.origin_id
    cache_policy_id  = aws_cloudfront_cache_policy.wedding_cors.id

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
    acm_certificate_arn = local.ssl_cert.arn
    ssl_support_method  = "sni-only"
  }
}

resource "aws_route53_record" "wedding_website" {
  zone_id = data.aws_route53_zone.cert_zone.zone_id
  name    = data.aws_route53_zone.cert_zone.name
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.wedding_website.domain_name
    zone_id                = aws_cloudfront_distribution.wedding_website.hosted_zone_id
    evaluate_target_health = false
  }
}
