output "kms_key_arn" {
  value       = "${aws_kms_key.enc.arn}"
  description = "ARN of the kms key used for general encryption"
}

output "kms_key_id" {
  value       = "${aws_kms_key.enc.id}"
  description = "id of the kms key used for general encryption"
}
