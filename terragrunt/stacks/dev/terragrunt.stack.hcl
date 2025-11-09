stack "dev" {
  source = "${get_repo_root()}/terragrunt//stacks/environment"
  path   = "dev"
  values = {
    env = "dev"
  }
}
