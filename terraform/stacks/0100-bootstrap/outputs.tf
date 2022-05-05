output "kms_key" {
  value = {
    for k, v in aws_kms_key.enc :
    k => v if contains(["arn", "id"], k)
  }
  description = "the KMS key used for general encryption"
}
