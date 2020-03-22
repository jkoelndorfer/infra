output "user_data" {
  description = "user data to be passed to the an EC2 instance"

  value = jsonencode({
    asg_name = var.asg_name
    category = var.category
    dns      = var.dns
    extra    = var.extra
    env      = var.env
    name     = var.name
    role     = var.role
  })
}
