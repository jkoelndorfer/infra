locals {
  backup_container_base = {
    image = "{{ workflow.parameters.ctrimage }}"
    env = [
      {
        name = "GOOGLE_CHAT_WEBHOOK_URL"
        valueFrom = {
          secretKeyRef = {
            name = "google-chat-webhook"
            key  = "url"
          }
        }
      },
      {
        name = "AWS_ACCESS_KEY_ID"
        valueFrom = {
          secretKeyRef = {
            name = "aws-backup"
            key  = "aws_access_key_id"
          }
        }
      },

      {
        name = "AWS_SECRET_ACCESS_KEY"
        valueFrom = {
          secretKeyRef = {
            name = "aws-backup"
            key  = "aws_secret_access_key"
          }
        }
      },
      {
        name  = "RESTIC_HOST"
        value = local.restic_host
      },
      # These are mostly present for reference if we ever exec
      # into the backup container.
      {
        name  = "BACKUP_S3_BUCKET"
        value = local.backup_s3_bucket
      },
      {
        name  = "BACKUP_S3_ROOT"
        value = local.backup_s3_root
      },
      {
        name  = "BACKUP_S3_RCLONE_REPOSITORY"
        value = local.backup_s3_rclone_repository
      },
      {
        name  = "BACKUP_S3_RESTIC_REPOSITORY"
        value = local.backup_s3_restic_repository
      },
      {
        name  = "BACKUP_S3_RESTIC_CACHE_DIR"
        value = local.backup_s3_restic_cache_dir
      },
      {
        name  = "BACKUP_LOCAL_RESTIC_REPOSITORY"
        value = local.backup_local_restic_repository
      },
      {
        name  = "BACKUP_LOCAL_RESTIC_CACHE_DIR"
        value = local.backup_local_restic_cache_dir
      },
      {
        name  = "BACKUP_RESTIC_PASSWORD_FILE"
        value = local.backup_restic_password_file
      },
      {
        name  = "TZ"
        value = var.backup_time.timezone
      },
    ]
  }

  scale_params = {
    syncthing = [
      {
        name  = "kind"
        value = "deployment"
      },
      {
        name  = "namespace"
        value = var.syncthing_deployment.namespace
      },
      {
        name  = "name"
        value = var.syncthing_deployment.name
      },
    ]
  }

  workflow_templates = [
    {
      name = "full-backup-run"
      dag = {
        tasks = local.workflow_tasks
      }
    },

    {
      name = "scale-app"
      inputs = {
        parameters = [
          { name = "kind" },
          { name = "namespace" },
          { name = "name" },
          { name = "replicas" },
        ]
      }

      container = {
        image = "{{ workflow.parameters.ctrimage }}"
        command = [
          "bash",
          "-c",
          <<-EOT
            set -euxo pipefail
            kubectl -n "$NAMESPACE" scale --replicas="$REPLICAS" "$${KIND}/$${NAME}"
            kubectl -n "$NAMESPACE" rollout status --watch "$${KIND}/$${NAME}"
          EOT
        ]
        env = [
          {
            name  = "KIND"
            value = "{{ inputs.parameters.kind }}"
          },
          {
            name  = "NAMESPACE"
            value = "{{ inputs.parameters.namespace }}"
          },
          {
            name  = "NAME"
            value = "{{ inputs.parameters.name }}"
          },
          {
            name  = "REPLICAS"
            value = "{{ inputs.parameters.replicas }}"
          },
        ]
      }

    },

    {
      name = "restic-backup"

      inputs = {
        parameters = [
          { name = "name" },
          { name = "path" },
        ]
      }

      container = {
        image = "{{ workflow.parameters.ctrimage }}"
        command = [
          "/app/backup.py",
          "--reporter",
          "googlechat",
          "--name",
          "{{ inputs.parameters.name }}",
          "restic",
          "--repository",
          local.backup_local_restic_repository,
          "--cache-dir",
          local.backup_local_restic_cache_dir,
          "--password-file",
          local.backup_restic_password_file,
          "backup",
          "{{ inputs.parameters.path }}",
        ]
        env = local.backup_container_base.env

        volumeMounts = [
          {
            name      = "local-backup"
            mountPath = local.backup_volume_path
          },
          {
            name      = "syncthing-config"
            mountPath = local.syncthing_config_volume_path
            readOnly  = true
          },
          {
            name      = "syncthing-data"
            mountPath = local.syncthing_data_volume_path
            readOnly  = true
          },
          {
            name      = "secrets"
            mountPath = local.secret_volume_path
            readOnly  = true
          },
        ]
      }
    },

    {
      name    = "restic-check"
      depends = "restic-backup-syncthing-data"

      container = {
        image = "{{ workflow.parameters.ctrimage }}"
        command = [
          "/app/backup.py",
          "--reporter",
          "googlechat",
          "--name",
          "Restic Check",
          "restic",
          "--repository",
          local.backup_local_restic_repository,
          "--cache-dir",
          local.backup_local_restic_cache_dir,
          "--password-file",
          local.backup_restic_password_file,
          "check",
        ]
        env = local.backup_container_base.env,

        volumeMounts = [
          {
            name      = "local-backup"
            mountPath = local.backup_volume_path
          },
          {
            name      = "secrets"
            mountPath = local.secret_volume_path
            readOnly  = true
          },
        ]
      }
    },

    {
      name    = "rclone-to-s3"
      depends = "restic-backup-syncthing"

      container = {
        image = "{{ workflow.parameters.ctrimage }}"
        command = [
          "/app/backup.py",
          "--reporter",
          "googlechat",
          "--name",
          "S3 Restic Repository",
          "rclone",
          "--s3-storage-class",
          "STANDARD",
          "--bwlimit",
          local.backup_bwlimit,
          "sync",
          local.backup_local_restic_repository,
          local.backup_s3_rclone_repository,
        ]
        env = local.backup_container_base.env,

        volumeMounts = [
          {
            name      = "local-backup"
            mountPath = local.backup_volume_path
            readOnly  = true
          },
        ]
      }
    },

    {
      name    = "compare-latest-snapshot"
      depends = "rclone-to-s3"

      container = {
        image = "{{ workflow.parameters.ctrimage }}"
        command = [
          "/app/backup.py",
          "--reporter",
          "googlechat",
          "--name",
          "Snapshot Comparison",
          "restic",
          "--repository",
          local.backup_local_restic_repository,
          "--cache-dir",
          local.backup_local_restic_cache_dir,
          "--password-file",
          local.backup_restic_password_file,
          "compare-latest-snapshots",
          local.backup_s3_restic_repository,
        ]
        env = local.backup_container_base.env,

        volumeMounts = [
          {
            name      = "local-backup"
            mountPath = local.backup_volume_path
          },
          {
            name      = "secrets"
            mountPath = local.secret_volume_path
            readOnly  = true
          },
        ]
      }
    },
  ]

  workflow_tasks = [
    {
      name     = "scale-down-syncthing"
      template = "scale-app"
      arguments = {
        parameters = concat(local.scale_params.syncthing, [{ name = "replicas", value = "0" }])
      }
    },

    {
      name     = "restic-backup-syncthing-data"
      template = "restic-backup"
      arguments = {
        parameters = [
          {
            name  = "name"
            value = "Backup Syncthing Data"
          },
          {
            name  = "path"
            value = local.syncthing_data_volume_path
          }
        ]
      }
      depends = "scale-down-syncthing"
    },

    {
      name     = "restic-backup-config"
      template = "restic-backup"
      arguments = {
        parameters = [
          {
            name  = "name"
            value = "Backup Config"
          },
          {
            name  = "path"
            value = local.config_path
          }
        ]
      }
      depends = "scale-down-syncthing"
    },

    {
      name     = "restic-check"
      template = "restic-check"
      arguments = {
        parameters = []
      }
      depends = join(
        " && ",
        [
          for s in ["restic-backup-config", "restic-backup-syncthing-data"] :
          "( ${s}.Succeeded || ${s}.Failed || ${s}.Errored )"
        ]
      )
    },

    {
      name     = "scale-up-syncthing"
      template = "scale-app"
      arguments = {
        parameters = concat(local.scale_params.syncthing, [{ name = "replicas", value = "1" }])
      }
      depends = join(
        " && ",
        [
          for s in ["restic-backup-config", "restic-backup-syncthing-data"] :
          "( ${s}.Succeeded || ${s}.Failed || ${s}.Errored )"
        ]
      )
    },

    {
      name     = "rclone-to-s3"
      template = "rclone-to-s3"
      arguments = {
        parameters = []
      }
      depends = "restic-check.Succeeded"
    },

    {
      name     = "compare-latest-snapshot"
      template = "compare-latest-snapshot"
      arguments = {
        parameters = []
      }
      depends = "rclone-to-s3.Succeeded"
    }
  ]
}

resource "kubernetes_manifest" "backup_workflow" {
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "CronWorkflow"

    metadata = {
      namespace = module.namespace.name
      name      = "backup"
    }

    spec = {
      schedule = "${var.backup_time.minute} ${var.backup_time.hour} * * *"
      timezone = var.backup_time.timezone

      concurrencyPolicy       = "Forbid"
      startingDeadlineSeconds = 60 * 30

      successfulJobsHistoryLimit = 3
      failedJobsHistoryLimit     = 3

      workflowSpec = {
        entrypoint = "full-backup-run"
        arguments = {
          parameters = [
            {
              name  = "ctrimage"
              value = local.backup_ctr_image
            },
          ]
        }

        imagePullSecrets   = [{ name = "image-pull" }]
        serviceAccountName = kubernetes_service_account_v1.backup.metadata[0].name

        templates = local.workflow_templates

        volumes = [
          {
            name = "local-backup"
            persistentVolumeClaim = {
              claimName = module.local_backup_volume.pvc.name
            }
          },

          {
            name = "syncthing-config"
            persistentVolumeClaim = {
              claimName = module.syncthing_config_volume.pvc.name
            }
          },

          {
            name = "syncthing-data"
            persistentVolumeClaim = {
              claimName = module.syncthing_data_volume.pvc.name
            }
          },

          {
            name = "secrets"
            secret = {
              secretName = "restic",
              items = [
                {
                  key  = "repository_password"
                  path = basename(local.backup_restic_password_file)
                },
              ]
            }
          },
        ]
      }
    }
  }
}
