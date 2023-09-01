locals {
  environments = {
    dev = {
      home_cname_records = [
        "vpn",
      ]
      miniserv_private_records = [
        "miniserv",
        "photoprism",
        "pihole",
        "syncthing",
        "unifi",
        "vaultwarden",
      ]
      miniserv_private_ip = "192.168.192.10"
    }
    prod = {
      home_cname_records = [
        "vpn",
      ]
      miniserv_private_records = [
        "miniserv",
        "photoprism",
        "pihole",
        "syncthing",
        "unifi",
        "vaultwarden",
      ]
      miniserv_private_ip = "192.168.192.10"
    }
  }
}
