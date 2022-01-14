locals {
  environments = {
    dev = {
      backup_vol_size = 5
    }
    prod = {
      backup_vol_size = 50
    }
  }
}
