output "dyndns_url" {
  value       = local.dyndns_url
  description = "URL of dynamic DNS service"
}

output "ec2_default_keypair" {
  value       = "${aws_key_pair.default.id}"
  description = "the ID of the default ec2 key pair"
}

output "ec2_default_instance_profile" {
  value       = "${aws_iam_instance_profile.instance_profile.name}"
  description = "the ID of the EC2 instance profile containing minimum permissions"
}

output "ec2_default_role" {
  value       = "${aws_iam_role.role.name}"
  description = "the ID of the default role that EC2 instances are are assigned"
}

output "ec2_default_policy_arn" {
  value       = "${aws_iam_policy.ec2_default_policy.arn}"
  description = "the ARN of the base policy for EC2 instances"
}

output "infra_s3_bucket" {
  value       = "${module.infra_s3_bucket.id}"
  description = "S3 bucket that is used for general infrastructure tasks"
}

output "lambda_logging_policy_arn" {
  value       = "${aws_iam_policy.lambda_logging.arn}"
  description = "ARN of IAM policy that permits Lambda to log to CloudWatch"
}

output "vpc_id" {
  value       = "${module.vpc.vpc_id}"
  description = "the ID of the core VPC"
}

output "vpc_cidr_block" {
  value       = "${module.vpc.vpc_cidr_block}"
  description = "the CIDR block of the core VPC"
}

output "vpc_default_sg" {
  value       = "${module.vpc.default_sg_id}"
  description = "the ID of the default security group for the VPC"
}
