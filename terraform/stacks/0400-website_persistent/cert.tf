resource "aws_acm_certificate" "website" {
  domain_name       = local.env.dns_zone
  validation_method = "DNS"

  subject_alternative_names = ["www.${local.env.dns_zone}"]

  lifecycle {
    create_before_destroy = true
  }
}

# Terraform cannot determine how many elements are in domain_validation_options until
# after the aws_acm_certificate resource is created, and so refuses to run when starting
# from nothing.
#
# To mitigate this, we move the validation resources to the non-persistent stack.
