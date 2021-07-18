data "terraform_remote_state" "blog_persistent" {
  backend   = "s3"
  workspace = terraform.workspace

  config = {
    bucket               = "310987624463-tfstate-prod"
    key                  = "blog_persistent.tfstate"
    region               = "us-east-1"
    workspace_key_prefix = "workspaces"
  }
}
