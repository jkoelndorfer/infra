module "s3_bucket" {
  source = "../../modules/aws-encrypted-s3-bucket/v1"

  bucket     = "backups"
  category   = "backup"
  env        = local.env.name
  versioning = "true"

  lifecycle_rules = [
    {
      id     = "deep-archive"
      prefix = "deep-archive/"

      transitions = [
        {
          days          = 30
          storage_class = "DEEP_ARCHIVE"
        },
      ]

      noncurrent_version_transitions = []

      noncurrent_version_expiration = {
        days = 1
      }
    },
    {
      id     = "rclone-syncthing-backups"
      prefix = "syncthing/rclone/"

      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
      ]

      noncurrent_version_transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
      ]

      noncurrent_version_expiration = {
        days = 90
      }
    },
    {
      id     = "rclone-duplicity-backups"
      prefix = "syncthing/duplicity/"

      transitions = []

      noncurrent_version_transitions = []

      noncurrent_version_expiration = {
        days = 1
      }
    },
  ]
}

# E-mail subscriptions are unsupported in Terraform because they must be confirmed
# by the e-mail address's owner. As such, we can't set the subscription up here.
# Since there is manual setup involved, this topic is a persistent resource.
#
# Don't forget to manually set up an SNS subscription! FeelsBadMan.
resource "aws_sns_topic" "backup_notifications" {
  name = "backup-notifications-${local.env.name}"
}
