resource "aws_ssm_parameter" "air_quality_access_key_id" {
  name  = "/prod/air_quality/aws_iam_access_key_id"
  value = aws_iam_access_key.air_quality.id
  type  = "String"
}

resource "aws_ssm_parameter" "air_quality_secret_access_key" {
  name  = "/prod/air_quality/aws_iam_secret_access_key"
  value = aws_iam_access_key.air_quality.secret
  type  = "SecureString"
}
