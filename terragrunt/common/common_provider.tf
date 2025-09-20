locals {
  default_labels = {
    env = var.env
  }
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.10.0"
    }

    google = {
      source  = "hashicorp/google"
      version = "6.46.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "3.7.2"
    }
  }
}

provider "random" {}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "homelab"
}
