variable "addl_apex_txt_rrdata" {
  description = "a list of additional rrdatas accompanying the SPF record"
  type        = list(string)
  default     = []
}

variable "dkim_rrdata" {
  description = "the data for the DKIM record"
  type        = string
}

variable "dmarc_rrdata" {
  description = "the value for the DMARC record"
  type        = string
}

variable "zone" {
  description = "the zone to configure email records for"
  type        = object({name = string, dns_name = string, project = string })
}
