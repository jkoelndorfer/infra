output "vpc" {
  value       = aws_vpc.vpc
  description = "the created VPC"
}

output "default_gateway" {
  value       = aws_internet_gateway.default_gateway
  description = "the default gateway of the created VPC"
}

output "default_sg" {
  value       = aws_security_group.default_sg
  description = "the default security group of the created VPC"
}
