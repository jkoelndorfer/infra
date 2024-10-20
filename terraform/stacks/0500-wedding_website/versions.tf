terraform {
  required_version = ">= 1.0.2"
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.6.0"
    }

    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.72.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.3"
    }
  }
}
