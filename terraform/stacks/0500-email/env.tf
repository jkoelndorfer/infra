locals {
  environments = {
    prod = {
      aws_mail_region = "us-east-1"
      default_dns_ttl = 600
      spf_record      = "v=spf1 include:amazonses.com ~all"
      dmarc_record    = "v=DMARC1;p=quarantine;pct=100;fo=1"
      dns_zone        = "johnk.io"
    }
  }
}
