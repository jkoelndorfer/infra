locals {
  environments = {
    dev = {
      home_cname_records = [
        "vaultwarden",
      ]
    }
    prod = {
      home_cname_records = [
        "vaultwarden",
      ]
    }
  }
}
