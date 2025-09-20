resource "google_project_iam_custom_role" "dns_record_updater" {
  project = module.project.project_id

  role_id     = "custom.dns.recordUpdater"
  title       = "DNS Record Updater"
  description = "Provides access to update DNS records."
  permissions = [
    "dns.changes.create",
    "dns.changes.get",
    "dns.changes.list",
    "dns.managedZones.get",
    "dns.managedZones.list",
    "dns.resourceRecordSets.create",
    "dns.resourceRecordSets.delete",
    "dns.resourceRecordSets.get",
    "dns.resourceRecordSets.list",
    "dns.resourceRecordSets.update",
  ]
}
