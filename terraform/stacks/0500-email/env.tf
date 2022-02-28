locals {
  environments = {
    prod = {
      default_dns_ttl = 600

      ownership_verification = "protonmail-verification=c0b1cbcaa68e509c32ea4c4e85d01dae3b491b1e"
      spf_record             = "v=spf1 include:_spf.protonmail.ch mx ~all"

      dkim_records = {
        protonmail  = "protonmail.domainkey.dbdts5dg2px7ags5zzewhcfpqelug5qq35btpwbnil42vmy6ipsza.domains.proton.ch."
        protonmail2 = "protonmail2.domainkey.dbdts5dg2px7ags5zzewhcfpqelug5qq35btpwbnil42vmy6ipsza.domains.proton.ch."
        protonmail3 = "protonmail3.domainkey.dbdts5dg2px7ags5zzewhcfpqelug5qq35btpwbnil42vmy6ipsza.domains.proton.ch."
      }
      mx_records = [
        "10 mail.protonmail.ch",
        "20 mailsec.protonmail.ch",
      ]
      dmarc_record = "v=DMARC1;p=quarantine;pct=100;fo=1"
      dns_zone     = "johnk.io"
    }
  }
}
