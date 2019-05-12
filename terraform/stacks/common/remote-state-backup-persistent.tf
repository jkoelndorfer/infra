data "terraform_remote_state" "backup_persistent" {
  backend   = "s3"
  workspace = "${terraform.workspace}"
  config {
    bucket               = "310987624463-prod-tfstate"
    key                  = "backup_persistent.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "workspaces"
  }
}
