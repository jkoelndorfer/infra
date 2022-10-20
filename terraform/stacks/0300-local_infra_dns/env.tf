locals {
  environments = {
    dev = {
      home_cname_records = [
        "miniserv",
        "pihole",
        "syncthing",
        "unifi",
        "vaultwarden",
      ]
    }
    prod = {
      home_cname_records = [
        "miniserv",
        "pihole",
        "syncthing",
        "unifi",
        "vaultwarden",
      ]
    }
  }
}
