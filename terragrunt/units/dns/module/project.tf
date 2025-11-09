module "project" {
  source = "${var.paths.modules_root}/google_env_project"

  google_env_folder = var.google_env_folder
  function   = "dns"
  services = [
    "dns.googleapis.com",
  ]
}
