output "dyndns_url" {
  value       = local.dyndns_url
  description = "URL of dynamic DNS service"
}

output "ec2_default_keypair" {
  value = {
    for k, v in aws_key_pair.default:
      k => v if contains(["arn", "id", "key_name"], k)
  }
  description = "the default EC2 key pair"
}

output "ec2_default_instance_profile" {
  value = {
    for k, v in aws_iam_instance_profile.instance_profile:
      k => v if contains(["arn", "id", "name", "role", "unique_id"], k)
  }
  description = "the EC2 instance profile containing the minimum set of permissions"
}

output "ec2_default_role" {
  value = {
    for k, v in aws_iam_role.role:
      k => v if contains(["arn", "name"], k)
  }
  description = "the default role that EC2 instances are are assigned"
}

output "ec2_default_policy" {
  value = {
    for k, v in aws_iam_policy.ec2_default_policy:
      k => v if contains(["arn", "name"], k)
  }
  description = "the base policy for EC2 instances"
}

output "infra_s3_bucket" {
  value = {
    for k, v in module.infra_s3_bucket.bucket:
      k => v if contains(["arn", "bucket"], k)
  }
  description = "S3 bucket that is used for general infrastructure tasks"
}

output "lambda_logging_policy_arn" {
  value = {
    for k, v in aws_iam_policy.lambda_logging:
      k => v if contains(["arn", "name"], k)
  }
  description = "ARN of IAM policy that permits Lambda to log to CloudWatch"
}

output "vpc" {
  value = {
    for k, v in module.vpc.vpc:
      k => v if contains(["arn", "cidr_block", "id"], k)
  }
  description = "the core VPC"
}

output "vpc_default_sg" {
  value = {
    for k, v in module.vpc.default_sg:
      k => v if contains(["arn", "id"], k)
  }
  description = "the default security group of the core VPC"
}
