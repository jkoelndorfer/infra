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
        name  = "BACKUP_VOLUME_PATH"
        value = local.backup_volume_path
      },
      {
        name  = "RESTIC_REPO_PATH"
        value = local.restic_repo_path
      },
      {
        name  = "RESTIC_CACHE_PATH"
        value = local.restic_cache_path
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
      name    = "restic-backup-syncthing"
      depends = "scale-down-syncthing"

      container = {
        image = "{{ workflow.parameters.ctrimage }}"
        command = [
          "/app/backup.py",
          "--reporter",
          "googlechat",
          "--name",
          "Backup Syncthing",
          "restic",
          "--repository",
          local.restic_repo_path,
          "--cache-dir",
          local.restic_cache_path,
          "--password-file",
          local.restic_password_file,
          "backup",
          local.syncthing_volume_path,
        ]
        env = local.backup_container_base.env

        volumeMounts = [
          {
            name      = "local-backup"
            mountPath = local.backup_volume_path
          },
          {
            name      = "syncthing-data"
            mountPath = local.syncthing_volume_path
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
      depends = "restic-backup-syncthing"

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
          local.restic_repo_path,
          "--cache-dir",
          local.restic_cache_path,
          "--password-file",
          local.restic_password_file,
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
          local.restic_repo_path,
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
          local.restic_repo_path,
          "--cache-dir",
          local.restic_cache_path,
          "--password-file",
          local.restic_password_file,
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
      name     = "restic-backup-syncthing"
      template = "restic-backup-syncthing"
      arguments = {
        parameters = []
      }
      depends = "scale-down-syncthing"
    },

    {
      name     = "restic-check"
      template = "restic-check"
      arguments = {
        parameters = []
      }
      depends = "restic-backup-syncthing.Succeeded || restic-backup-syncthing.Failed || restic-backup-syncthing.Errored"
    },

    {
      name     = "scale-up-syncthing"
      template = "scale-app"
      arguments = {
        parameters = concat(local.scale_params.syncthing, [{ name = "replicas", value = "1" }])
      }
      depends = "restic-backup-syncthing.Succeeded || restic-backup-syncthing.Failed || restic-backup-syncthing.Errored"
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
                  path = basename(local.restic_password_file)
                },
              ]
            }
          },
        ]
      }
    }
  }
}
