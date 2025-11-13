# This deployment will provision a pod that can be exec'd into
# for backup code development purposes.
resource "kubernetes_deployment_v1" "backup_debug" {
  metadata {
    namespace = module.namespace.name
    name      = "backup-debug"
  }

  spec {
    # By default, provision 0 replicas. Scale this deployment out
    # manually if backups require debugging.
    replicas = 0

    selector {
      match_labels = {
        "local/backup-debug" = "true"
      }
    }

    template {
      metadata {
        namespace = module.namespace.name
        name      = "backup-debug"
        labels = {
          "local/backup-debug" = "true"
        }
      }

      spec {
        image_pull_secrets {
          name = kubernetes_secret_v1.registry_image_pull.metadata[0].name
        }

        container {
          name  = "backup-debug"
          image = local.backup_ctr_image

          image_pull_policy = "Always"

          command = [
            "bash",
            "-c",
            "while true; do sleep 3; done",
          ]

          env {
            name  = "AWS_DEFAULT_REGION"
            value = "us-east-2"
          }

          env {
            name = "AWS_ACCESS_KEY_ID"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.aws_backup.metadata[0].name
                key  = "aws_access_key_id"
              }
            }
          }

          env {
            name = "AWS_SECRET_ACCESS_KEY"
            value_from {
              secret_key_ref {
                name = kubernetes_secret_v1.aws_backup.metadata[0].name
                key  = "aws_secret_access_key"
              }
            }
          }

          env {
            name  = "BACKUP_LOCAL_RESTIC_REPOSITORY"
            value = local.backup_local_restic_repository
          }

          env {
            name  = "BACKUP_S3_BUCKET"
            value = local.backup_s3_bucket
          }

          env {
            name  = "BACKUP_S3_ROOT"
            value = local.backup_s3_root
          }

          env {
            name  = "BACKUP_S3_RCLONE_REPOSITORY"
            value = local.backup_s3_rclone_repository
          }

          env {
            name  = "BACKUP_S3_RESTIC_REPOSITORY"
            value = local.backup_s3_restic_repository
          }

          env {
            name  = "BACKUP_S3_RESTIC_CACHE_DIR"
            value = local.backup_s3_restic_cache_dir
          }

          env {
            name  = "BACKUP_RESTIC_PASSWORD_FILE"
            value = local.backup_restic_password_file
          }

          env {
            name  = "BACKUP_LOCAL_RESTIC_CACHE_DIR"
            value = local.backup_local_restic_cache_dir
          }

          env {
            name  = "RESTIC_HOST"
            value = local.restic_host
          }

          volume_mount {
            name       = "local-backup"
            mount_path = local.backup_volume_path
          }

          volume_mount {
            name       = "syncthing-config"
            read_only  = true
            mount_path = local.syncthing_config_volume_path
          }

          volume_mount {
            name       = "syncthing-data"
            read_only  = true
            mount_path = local.syncthing_data_volume_path
          }

          volume_mount {
            name       = "secrets"
            read_only  = true
            mount_path = local.secret_volume_path
          }
        }

        volume {
          name = "local-backup"
          persistent_volume_claim {
            claim_name = module.local_backup_volume.pvc.name
          }
        }

        volume {
          name = "syncthing-config"
          persistent_volume_claim {
            claim_name = module.syncthing_config_volume.pvc.name
          }
        }

        volume {
          name = "syncthing-data"
          persistent_volume_claim {
            claim_name = module.syncthing_data_volume.pvc.name
          }
        }

        volume {
          name = "secrets"
          secret {
            default_mode = "0400"
            secret_name  = "restic"
            items {
              key  = "repository_password"
              path = "restic-repository-password"
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      spec[0].replicas,
    ]
  }
}
