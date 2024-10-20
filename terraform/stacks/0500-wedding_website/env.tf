locals {
  environments = {
    dev  = {
      dns_zone = "dev.koelndorfer.wedding"
    }
    prod = {
      dns_zone = "koelndorfer.wedding"
    }
  }
}
