stack "prod" {
  source = "${get_repo_root()}/terragrunt//stacks/environment"
  path   = "prod"
  values = {
    env = "prod"
  }
}
