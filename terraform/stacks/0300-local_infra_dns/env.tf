locals {
  environments = {
    dev = {
      home_cname_records = [
        "miniserv",
        "pihole",
        "syncthing",
        "unifi",
        "vaultwarden",
        "vpn",
      ]
    }
    prod = {
      home_cname_records = [
        "miniserv",
        "pihole",
        "syncthing",
        "unifi",
        "vaultwarden",
        "vpn",
      ]
    }
  }
}
