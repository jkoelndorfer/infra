data "terraform_remote_state" "air_quality" {
  backend   = "s3"
  workspace = terraform.workspace
  config = {
    bucket               = "310987624463-tfstate-prod"
    key                  = "air_quality.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "workspaces"
  }
}
