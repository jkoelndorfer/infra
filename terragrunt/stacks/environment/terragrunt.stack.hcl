unit "env_folder" {
  source = "${get_repo_root()}/terragrunt//units/env_folder/"
  path   = "env_folder"
  values = {
    env = values.env
  }
}
