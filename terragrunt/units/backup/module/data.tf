locals {
  # The container image used to perform backups.
  backup_ctr_image = "${data.kubernetes_secret_v1.registry_ro.data.hostname}/${var.backup_image}"

  # The bandwidth limit (--bwlimit) to pass to rclone.
  backup_bwlimit = "00:00,off 07:00,2M:12M"

  # The AWS CLI compatible S3 backup bucket path.
  backup_s3_root = "s3://${aws_s3_bucket.backup.bucket}"

  # The rclone path to the S3-hosted restic backup repository.
  backup_s3_rclone_repository = ":s3:${aws_s3_bucket.backup.bucket}/restic"

  # The restic path to the S3-hosted restic backup repository.
  backup_s3_restic_repository = "s3:https://s3.amazonaws.com/${aws_s3_bucket.backup.bucket}/restic"

  # The local backup container path to the volume containing the restic repository.
  backup_volume_path = "/data/backup"

  # The local backup container path to the volume containing secrets.
  secret_volume_path = "/secret"

  # The path to the restic password file.
  restic_password_file = "${local.secret_volume_path}/restic-repository-password"

  # The local backup container path to the the restic repository.
  restic_repo_path = "${local.backup_volume_path}/restic"

  # The local backup container path to the the restic cache directory.
  restic_cache_path = "${local.backup_volume_path}/.restic-cache"

  # The host used by restic for backups.
  restic_host = "kserv"

  # The local backup container path to the volume containing syncthing data.
  syncthing_volume_path = "/data/syncthing"
}
