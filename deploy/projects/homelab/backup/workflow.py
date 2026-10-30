"""
projects.homelab.backup.workflow
================================

This module contains the Argo CronWorkflow that performs backups.
"""

from typing import Any

from pulumi import Input, Output, ResourceOptions
import pulumi_kubernetes as k8s

from infralib import DeploymentContext

from ..syncthing import HomelabSyncthingProject
from ..vaultwarden import HomelabVaultwardenProject
from .volume import RefVolumeProvisionResult

SCHEDULE = "0 3 * * *"
TIMEZONE = "America/Chicago"

BWLIMIT = "00:00,off 07:00,2M:12M"
"""
The bandwidth limit (--bwlimit) to pass to rclone.
"""

RESTIC_HOST = "kserv"
"""
The host used by restic for backups.
"""

BACKUP_VOLUME_PATH = "/data/backup"
CACHES_DIR = f"{BACKUP_VOLUME_PATH}/caches"
LOCAL_RESTIC_REPOSITORY = f"{BACKUP_VOLUME_PATH}/restic"
LOCAL_RESTIC_CACHE_DIR = f"{CACHES_DIR}/local"
S3_RESTIC_CACHE_DIR = f"{CACHES_DIR}/s3"

SECRET_VOLUME_PATH = "/secret"
RESTIC_PASSWORD_FILENAME = "restic-repository-password"
RESTIC_PASSWORD_FILE = f"{SECRET_VOLUME_PATH}/{RESTIC_PASSWORD_FILENAME}"

CONFIG_PATH = "/config"
SYNCTHING_CONFIG_VOLUME_PATH = f"{CONFIG_PATH}/syncthing"
SYNCTHING_DATA_VOLUME_PATH = "/data/syncthing"
VAULTWARDEN_DATA_VOLUME_PATH = "/data/vaultwarden"

CTR_IMAGE = "{{ workflow.parameters.ctrimage }}"

BACKUP_MOUNT = {"name": "local-backup", "mountPath": BACKUP_VOLUME_PATH}
SECRETS_MOUNT = {"name": "secrets", "mountPath": SECRET_VOLUME_PATH, "readOnly": True}


def _secret_env(name: str, secret_name: str, key: str) -> dict[str, Any]:
    """
    Returns a container environment variable sourced from a secret.
    """
    return {
        "name": name,
        "valueFrom": {"secretKeyRef": {"name": secret_name, "key": key}},
    }


def _env(env: dict[str, Input[str]]) -> list[dict[str, Input[str]]]:
    """
    Returns container environment variables with the given literal values.
    """
    return [{"name": k, "value": v} for k, v in env.items()]


def _params(params: dict[str, Input[str]]) -> dict[str, Any]:
    """
    Returns task arguments with the given parameter values.
    """
    return {"parameters": _env(params)}


def _inputs(*names: str) -> dict[str, Any]:
    """
    Returns template inputs that accept the given parameter names.
    """
    return {"parameters": [{"name": n} for n in names]}


def _finished(task: str) -> str:
    """
    Returns a depends expression that is true once the task has run, regardless
    of whether it was successful.
    """
    return f"{task}.Succeeded || {task}.Failed || {task}.Errored"


def _all_finished(*tasks: str) -> str:
    """
    Returns a depends expression that is true once all tasks have run,
    regardless of whether they were successful.
    """
    return " && ".join(f"( {_finished(t)} )" for t in tasks)


def _backup_container_env(bucket_name: Input[str]) -> list[dict[str, Any]]:
    """
    Returns the environment shared by containers that perform backups.
    """
    return [
        _secret_env("GOOGLE_CHAT_WEBHOOK_URL", "google-chat-webhook", "url"),
        _secret_env("AWS_ACCESS_KEY_ID", "aws-backup", "aws_access_key_id"),
        _secret_env("AWS_SECRET_ACCESS_KEY", "aws-backup", "aws_secret_access_key"),
        # Other than RESTIC_HOST and TZ, these are mostly present for reference
        # if we ever exec into the backup container.
        *_env(
            {
                "RESTIC_HOST": RESTIC_HOST,
                "BACKUP_S3_BUCKET": bucket_name,
                "BACKUP_S3_ROOT": Output.concat("s3://", bucket_name),
                "BACKUP_S3_RCLONE_REPOSITORY": _s3_rclone_repository(bucket_name),
                "BACKUP_S3_RESTIC_REPOSITORY": _s3_restic_repository(bucket_name),
                "BACKUP_S3_RESTIC_CACHE_DIR": S3_RESTIC_CACHE_DIR,
                "BACKUP_LOCAL_RESTIC_REPOSITORY": LOCAL_RESTIC_REPOSITORY,
                "BACKUP_LOCAL_RESTIC_CACHE_DIR": LOCAL_RESTIC_CACHE_DIR,
                "BACKUP_RESTIC_PASSWORD_FILE": RESTIC_PASSWORD_FILE,
                "TZ": TIMEZONE,
            }
        ),
    ]


def _s3_rclone_repository(bucket_name: Input[str]) -> Output[str]:
    """
    Returns the rclone path to the S3-hosted restic backup repository.
    """
    return Output.concat(":s3:", bucket_name, "/restic")


def _s3_restic_repository(bucket_name: Input[str]) -> Output[str]:
    """
    Returns the restic path to the S3-hosted restic backup repository.
    """
    return Output.concat("s3:https://s3.amazonaws.com/", bucket_name, "/restic")


def _restic_command(name: str, *subcommand: Input[str]) -> list[Input[str]]:
    """
    Returns a command that runs a reporting restic operation against the local
    repository.
    """
    return [
        "/app/backup.py",
        "--reporter",
        "googlechat",
        "--name",
        name,
        "restic",
        "--repository",
        LOCAL_RESTIC_REPOSITORY,
        "--cache-dir",
        LOCAL_RESTIC_CACHE_DIR,
        "--password-file",
        RESTIC_PASSWORD_FILE,
        *subcommand,
    ]


def _templates(
    tasks: list[dict[str, Any]],
    bucket_name: Input[str],
) -> list[dict[str, Any]]:
    """
    Returns the templates of the backup workflow.
    """
    env = _backup_container_env(bucket_name)

    return [
        {
            "name": "full-backup-run",
            "dag": {"tasks": tasks},
        },
        {
            "name": "scale-app",
            "inputs": _inputs("kind", "namespace", "name", "replicas"),
            "container": {
                "image": CTR_IMAGE,
                "command": [
                    "bash",
                    "-c",
                    "set -euxo pipefail\n"
                    'kubectl -n "$NAMESPACE" scale --replicas="$REPLICAS" "${KIND}/${NAME}"\n'
                    'kubectl -n "$NAMESPACE" rollout status --watch "${KIND}/${NAME}"\n',
                ],
                "env": _env(
                    {
                        "KIND": "{{ inputs.parameters.kind }}",
                        "NAMESPACE": "{{ inputs.parameters.namespace }}",
                        "NAME": "{{ inputs.parameters.name }}",
                        "REPLICAS": "{{ inputs.parameters.replicas }}",
                    }
                ),
            },
        },
        {
            "name": "restic-backup",
            "inputs": _inputs("name", "path"),
            "container": {
                "image": CTR_IMAGE,
                "command": _restic_command(
                    "{{ inputs.parameters.name }}",
                    "backup",
                    "{{ inputs.parameters.path }}",
                ),
                "env": env,
                "volumeMounts": [
                    BACKUP_MOUNT,
                    {
                        "name": "syncthing-config",
                        "mountPath": SYNCTHING_CONFIG_VOLUME_PATH,
                        "readOnly": True,
                    },
                    {
                        "name": "syncthing-data",
                        "mountPath": SYNCTHING_DATA_VOLUME_PATH,
                        "readOnly": True,
                    },
                    SECRETS_MOUNT,
                ],
            },
        },
        {
            "name": "restic-prune-repack",
            "container": {
                "image": CTR_IMAGE,
                "command": _restic_command(
                    "Prune/Repack",
                    "prune-repack",
                    "--keep-last",
                    "5",
                    "--keep-within-daily",
                    "30d",
                    "--keep-within-monthly",
                    "2y",
                    "--keep-within-yearly",
                    "5y",
                ),
                "env": env,
                "volumeMounts": [BACKUP_MOUNT, SECRETS_MOUNT],
            },
        },
        {
            "name": "restic-check",
            "container": {
                "image": CTR_IMAGE,
                "command": _restic_command("Restic Check", "check"),
                "env": env,
                "volumeMounts": [BACKUP_MOUNT, SECRETS_MOUNT],
            },
        },
        {
            "name": "local-rclone",
            "inputs": _inputs("source", "destination", "file_user", "file_group"),
            "container": {
                "image": CTR_IMAGE,
                "command": [
                    "bash",
                    "-c",
                    "set -euxo pipefail\n"
                    'rclone -v --checksum --stats=0 sync "$SOURCE" "$DESTINATION"\n'
                    'chown -R "${FILE_USER}:${FILE_GROUP}" "$DESTINATION"\n',
                ],
                "env": [
                    *env,
                    *_env(
                        {
                            "SOURCE": "{{ inputs.parameters.source }}",
                            "DESTINATION": "{{ inputs.parameters.destination }}",
                            "FILE_USER": "{{ inputs.parameters.file_user }}",
                            "FILE_GROUP": "{{ inputs.parameters.file_group }}",
                        }
                    ),
                ],
                # This is mounted read-write because data is copied into it. The
                # volume's ReadOnlyMany access mode is not enforced for local
                # persistent volumes.
                "volumeMounts": [
                    {
                        "name": "syncthing-data",
                        "mountPath": SYNCTHING_DATA_VOLUME_PATH,
                    },
                    {
                        "name": "vaultwarden-data",
                        "mountPath": VAULTWARDEN_DATA_VOLUME_PATH,
                        "readOnly": True,
                    },
                ],
            },
        },
        {
            "name": "rclone-to-s3",
            "container": {
                "image": CTR_IMAGE,
                "command": [
                    "/app/backup.py",
                    "--reporter",
                    "googlechat",
                    "--name",
                    "S3 Restic Repository",
                    "rclone",
                    "--s3-storage-class",
                    "STANDARD",
                    "--bwlimit",
                    BWLIMIT,
                    "sync",
                    LOCAL_RESTIC_REPOSITORY,
                    _s3_rclone_repository(bucket_name),
                ],
                "env": env,
                "volumeMounts": [{**BACKUP_MOUNT, "readOnly": True}],
            },
        },
        {
            "name": "compare-latest-snapshot",
            "container": {
                "image": CTR_IMAGE,
                "command": _restic_command(
                    "Snapshot Comparison",
                    "compare-latest-snapshots",
                    _s3_restic_repository(bucket_name),
                ),
                "env": env,
                "volumeMounts": [BACKUP_MOUNT, SECRETS_MOUNT],
            },
        },
    ]


def _tasks(dctx: DeploymentContext) -> list[dict[str, Any]]:
    """
    Returns the tasks of the backup workflow's DAG.
    """
    syncthing_pv = HomelabSyncthingProject.data_pv(dctx, dctx.target)
    vaultwarden_pv = HomelabVaultwardenProject.data_pv(dctx, dctx.target)

    def scale(
        task_name: str,
        namespace: str,
        name: str,
        replicas: int,
        depends: str | None = None,
    ) -> dict[str, Any]:
        task: dict[str, Any] = {
            "name": task_name,
            "template": "scale-app",
            "arguments": _params(
                {
                    "kind": "deployment",
                    "namespace": namespace,
                    "name": name,
                    "replicas": str(replicas),
                }
            ),
        }
        if depends is not None:
            task["depends"] = depends
        return task

    def scale_syncthing(
        task_name: str, replicas: int, depends: str | None = None
    ) -> dict[str, Any]:
        return scale(
            task_name,
            syncthing_pv.namespace,
            HomelabSyncthingProject.service_name,
            replicas,
            depends,
        )

    def scale_vaultwarden(
        task_name: str, replicas: int, depends: str | None = None
    ) -> dict[str, Any]:
        return scale(
            task_name,
            vaultwarden_pv.namespace,
            HomelabVaultwardenProject.service_name,
            replicas,
            depends,
        )

    restic_backups_finished = _all_finished(
        "restic-backup-config",
        "restic-backup-syncthing-data",
    )

    return [
        scale_vaultwarden("scale-down-vaultwarden", 0),
        scale_syncthing("scale-down-syncthing", 0),
        {
            "name": "copy-vaultwarden-data-to-syncthing",
            "template": "local-rclone",
            "arguments": _params(
                {
                    "source": VAULTWARDEN_DATA_VOLUME_PATH,
                    "destination": f"{SYNCTHING_DATA_VOLUME_PATH}/vaultwarden/data",
                    "file_user": str(syncthing_pv.user),
                    "file_group": str(syncthing_pv.group),
                }
            ),
            "depends": "scale-down-vaultwarden && scale-down-syncthing",
        },
        scale_vaultwarden(
            "scale-up-vaultwarden",
            1,
            _finished("copy-vaultwarden-data-to-syncthing"),
        ),
        {
            "name": "restic-backup-syncthing-data",
            "template": "restic-backup",
            "arguments": _params(
                {
                    "name": "Backup Syncthing Data",
                    "path": SYNCTHING_DATA_VOLUME_PATH,
                }
            ),
            "depends": "copy-vaultwarden-data-to-syncthing",
        },
        {
            "name": "restic-backup-config",
            "template": "restic-backup",
            "arguments": _params(
                {
                    "name": "Backup Config",
                    "path": CONFIG_PATH,
                }
            ),
            "depends": "scale-down-syncthing",
        },
        {
            "name": "restic-prune-repack",
            "template": "restic-prune-repack",
            "depends": restic_backups_finished,
        },
        {
            "name": "restic-check",
            "template": "restic-check",
            "depends": _finished("restic-prune-repack"),
        },
        scale_syncthing("scale-up-syncthing", 1, restic_backups_finished),
        {
            "name": "rclone-to-s3",
            "template": "rclone-to-s3",
            "depends": "restic-check.Succeeded",
        },
        {
            "name": "compare-latest-snapshot",
            "template": "compare-latest-snapshot",
            "depends": "rclone-to-s3.Succeeded",
        },
    ]


def provision_backup_workflow(
    dctx: DeploymentContext,
    namespace_name: Input[str],
    image: str,
    image_pull_secret: k8s.core.v1.Secret | None,
    service_account: k8s.core.v1.ServiceAccount,
    bucket_name: Input[str],
    local_backup_claim_name: Input[str],
    ref_volumes: RefVolumeProvisionResult,
    k8s_opts: ResourceOptions,
) -> k8s.apiextensions.CustomResource:
    """
    Provisions the CronWorkflow that performs backups.
    """

    # NOTE: The "google-chat-webhook" secret is referenced below, but it is not
    # managed here. It needs to be added to the backup namespace with a "url"
    # data key, the same as the "restic" secret described in kserv.py.
    #
    #     $ kubectl -n $NAMESPACE create secret generic google-chat-webhook
    #     $ kubectl -n $NAMESPACE edit secret/google-chat-webhook

    def pvc_volume(name: str, claim_name: Input[str]) -> dict[str, Any]:
        return {
            "name": name,
            "persistentVolumeClaim": {"claimName": claim_name},
        }

    image_pull_secrets = (
        [{"name": image_pull_secret.metadata.name}]
        if image_pull_secret is not None
        else []
    )

    return k8s.apiextensions.CustomResource(
        "backup_workflow",
        api_version="argoproj.io/v1alpha1",
        kind="CronWorkflow",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=namespace_name,
            name="backup",
        ),
        spec={
            "schedules": [SCHEDULE],
            "timezone": TIMEZONE,
            "concurrencyPolicy": "Forbid",
            "startingDeadlineSeconds": 60 * 30,
            "successfulJobsHistoryLimit": 3,
            "failedJobsHistoryLimit": 3,
            "workflowSpec": {
                "entrypoint": "full-backup-run",
                "arguments": _params({"ctrimage": image}),
                "imagePullSecrets": image_pull_secrets,
                "serviceAccountName": service_account.metadata.name,
                "templates": _templates(_tasks(dctx), bucket_name),
                "volumes": [
                    pvc_volume("local-backup", local_backup_claim_name),
                    pvc_volume(
                        "syncthing-config",
                        ref_volumes.syncthing_config.pvc.name,
                    ),
                    pvc_volume(
                        "syncthing-data",
                        ref_volumes.syncthing_data.pvc.name,
                    ),
                    pvc_volume(
                        "vaultwarden-data",
                        ref_volumes.vaultwarden_data.pvc.name,
                    ),
                    {
                        "name": "secrets",
                        "secret": {
                            "secretName": "restic",
                            "items": [
                                {
                                    "key": "repository_password",
                                    "path": RESTIC_PASSWORD_FILENAME,
                                },
                            ],
                        },
                    },
                ],
            },
        },
        opts=k8s_opts,
    )
