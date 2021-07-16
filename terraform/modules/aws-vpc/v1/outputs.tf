output "vpc_id" {
  value       = aws_vpc.vpc.id
  description = "the ID of the created VPC"
}

output "vpc_cidr_block" {
  value       = aws_vpc.vpc.cidr_block
  description = "the CIDR block assigned to the created VPC"
}

output "default_gateway_id" {
  value       = aws_internet_gateway.default_gateway.id
  description = "the ID of the default gateway for the VPC"
}

output "default_sg_id" {
  value       = aws_security_group.default_sg.id
  description = "the ID of the default security gorup for the VPC"
}
