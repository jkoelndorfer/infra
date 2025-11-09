module "manifest" {
  source = "../http_download"

  url       = var.url
  sha256sum = var.sha256sum
}

locals {
  # Decodes a YAML file containing multiple manifests into a list
  # of manifests.
  multi_manifest     = provider::kubernetes::manifest_decode_multi(file(module.manifest.file_path))
  multi_manifest_map = { for m in local.multi_manifest : "${m["apiVersion"]}/${m["Kind"]}/${lookup(m["metadata"], "namespace", "<global>")}/${m["metadata"]["name"]}" => m }
}

resource "kubernetes_manifest" "this" {
  for_each = local.multi_manifest_map

  manifest = each.value
}
