resource "google_service_account" "homelab_traefik" {
  project = var.homelab_dns_project.project_id

  account_id   = "homelab-traefik"
  display_name = "Homelab Traefik"
}

resource "google_service_account_key" "homelab_traefik" {
  service_account_id = google_service_account.homelab_traefik.name
}

resource "google_project_iam_member" "homelab_traefik_dns_updater" {
  project = var.homelab_dns_project.project_id

  member = google_service_account.homelab_traefik.member
  role   = var.homelab_dns_updater_role.id
}
