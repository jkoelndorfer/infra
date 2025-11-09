module "john_koelndorfer_com_email_records" {
  count  = module.org_primary_zone.zone_was_created ? 1 : 0
  source = "${var.paths.modules_root}/google_email_dns_records"

  addl_apex_txt_rrdata = ["google-site-verification=jAl7G_NnFx0XZ_5a3JxfhgAjzwoSmADNb_rKoH9WOY4"]
  dkim_rrdata          = "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCKcsBV2WtdcXI4r+kxmXlYwB6nbcyhwfXnTxzQw2iUuhkUkVEvwiOyJKoOWD6h4Z693MP4u3Jl4yeWOmXdnznAsmHwO2Fy/+xnc0ujtWwZnAgv+EV6Jriy7m7UXzmsePIeEgotnIJhepEDbqt5CZZkIzqZMZXGXdvmYgeYxFlRuQIDAQAB"
  dmarc_rrdata         = "v=DMARC1;p=none;pct=100;fo=1;rua=mailto:dmarc@john.${module.org_primary_zone.email_domain}"
  zone                 = merge(
    module.org_primary_zone,
    {
      dns_name = "john.${module.org_primary_zone.dns_name}"
    }
  )
}
