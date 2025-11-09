output "domains" {
  value = nonsensitive({for k, v in local.anonymous_domains : k => v if k != "//"})
}
