data "external" "download" {
  program = ["${path.module}/download"]

  query = {
    url       = var.url
    sha256sum = var.sha256sum
  }
}
