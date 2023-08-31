resource "aws_ssm_parameter" "backup_bucket" {
  name  = "/${local.env.name}/backup/bucket"
  type  = "String"
  value = data.terraform_remote_state.backup_persistent.outputs.s3_bucket.bucket
}
resource "aws_ssm_parameter" "syncthing_rclone_dest" {
  name  = "/${local.env.name}/backup/rclone_dest"
  type  = "String"
  value = "s3:${data.terraform_remote_state.backup_persistent.outputs.s3_bucket.bucket}/syncthing/rclone/data"
}

resource "aws_ssm_parameter" "backup_sns_topic_arn" {
  name  = "/${local.env.name}/backup/backup_sns_topic_arn"
  type  = "String"
  value = data.terraform_remote_state.backup_persistent.outputs.sns_topic.arn
}
