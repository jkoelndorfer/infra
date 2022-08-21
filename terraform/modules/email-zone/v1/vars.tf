variable "dmarc_record" {
  description = "the value of the DMARC record for the zone"
  type        = string
}

variable "dkim_records" {
  description = "a map of DKIM host records (the part before '_domainkey') to their CNAME values"
  type        = map(string)
}

variable "dns_ttl" {
  description = "the TTL of email records configured by this module"
  type        = number
}

variable "mx_records" {
  description = "the value of the MX record for the zone"
  type        = list(string)
}

variable "spf_record" {
  description = "the value of the SPF record for the zone"
}

variable "zone" {
  description = "the Route 53 zone to configure email for"
  type        = string
}
