resource "aws_ssm_parameter" "photoprism_user" {
  name  = "/${local.env.name}/photoprism/username"
  type  = "String"
  value = "photoprism"
}

resource "random_password" "photoprism_password" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "photoprism_password" {
  name  = "/${local.env.name}/photoprism/password"
  type  = "SecureString"
  value = random_password.photoprism_password.result
}
