locals {
  environments = {
    prod = {
      dns_ttl             = 600
      dmarc_record        = "v=DMARC1;p=quarantine;pct=100;fo=1"
      fastmail_spf_record = "v=spf1 include:spf.messagingengine.com ?all"

      koelndorfer_com = {
        dkim_records = {
          fm1 = "fm1.koelndorfer.com.dkim.fmhosted.com"
          fm2 = "fm2.koelndorfer.com.dkim.fmhosted.com"
          fm3 = "fm3.koelndorfer.com.dkim.fmhosted.com"
        }

        # Previously, koelndorfer.com had MX records pointing
        # at GMail:
        #
        # 10 alt2.aspmx.l.google.com.
        # 10 aspmx2.googlemail.com.
        # 10 alt1.aspmx.l.google.com.
        # 10 aspmx.l.google.com.
        # 10 aspmx3.googlemail.com.
        mx_records = [
          "10 in1-smtp.messagingengine.com",
          "20 in2-smtp.messagingengine.com",
        ]

        zone = "koelndorfer.com"
      }

      johnk_io = {
        dkim_records = {
          fm1 = "fm1.johnk.io.dkim.fmhosted.com"
          fm2 = "fm2.johnk.io.dkim.fmhosted.com"
          fm3 = "fm3.johnk.io.dkim.fmhosted.com"
        }

        mx_records = [
          "10 in1-smtp.messagingengine.com",
          "20 in2-smtp.messagingengine.com",
        ]

        zone = "johnk.io"
      }
    }
  }
}
