output "file_path" {
  description = "the path to the downloaded file"
  value       = data.external.download.result.file_path
}

output "file_downloaded" {
  description = "true if the file was downloaded during this run; false otherwise"
  value       = data.external.download.result.file_downloaded == "true" ? true : false
}
