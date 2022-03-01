locals {
  environments = {
    prod = {
      default_dns_ttl = 600

      spf_record = "v=spf1 include:spf.messagingengine.com ?all"

      dkim_records = {
        fm1 = "fm1.johnk.io.dkim.fmhosted.com"
        fm2 = "fm2.johnk.io.dkim.fmhosted.com"
        fm3 = "fm3.johnk.io.dkim.fmhosted.com"
      }
      mx_records = [
        "10 in1-smtp.messagingengine.com",
        "20 in2-smtp.messagingengine.com",
      ]
      dmarc_record = "v=DMARC1;p=quarantine;pct=100;fo=1"
      dns_zone     = "johnk.io"
    }
  }
}
