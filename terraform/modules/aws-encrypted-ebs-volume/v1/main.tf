resource "aws_ebs_volume" "ebs_volume" {
  availability_zone = var.availability_zone
  size              = var.size
  type              = var.type
  encrypted         = true
  kms_key_id        = var.kms_key_arn
  tags = {
    "Name"           = "${var.name}-${var.env}"
    "johnk:category" = var.category
    "johnk:role"     = var.role
    "johnk:env"      = var.env
  }
}
