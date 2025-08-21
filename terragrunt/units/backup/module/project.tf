module "project" {
  source = "${var.paths.modules_root}/google_env_project"

  env_folder = var.env_folder
  function   = "backup"
  services = [
    "storage.googleapis.com",
  ]
}

