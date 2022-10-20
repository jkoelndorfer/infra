locals {
  environments = {
    dev = {
      home_cname_records = [
        "pihole",
        "syncthing",
        "unifi",
        "vaultwarden",
      ]
    }
    prod = {
      home_cname_records = [
        "pihole",
        "syncthing",
        "unifi",
        "vaultwarden",
      ]
    }
  }
}
