# Homelab cloud DNS is provisioned in a different GCP project than the rest
# of the DNS zones because we may want to enable dynamic DNS managed via
# the homelab. The homelab should not be able to manage DNS records for
# email or cloud hosted sites.
module "project" {
  source = "${var.paths.modules_root}/google_env_project"

  google_env_folder = var.google_env_folder
  function          = "homelab-dns"
  services = [
    "dns.googleapis.com",
  ]
}
