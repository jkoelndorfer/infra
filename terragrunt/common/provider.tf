terraform {
  required_providers {
    google = {
      source  = "opentofu/google"
      version = "6.46.0"
    }

    random = {
      source  = "opentofu/random"
      version = "3.7.2"
    }
  }
}

provider "google" {
  default_labels = {
    env = var.env
  }
}

provider "random" {}
