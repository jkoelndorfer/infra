data "terraform_remote_state" "core" {
  backend   = "s3"
  workspace = "${terraform.workspace}"
  config = {
    bucket               = "310987624463-prod-tfstate"
    key                  = "core.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "workspaces"
  }
}
