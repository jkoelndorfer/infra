"""
projects.homelab.backup.debug
=============================

This module contains the backup debug deployment: a pod with the backup image,
credentials, and volumes, which can be exec'd into to inspect or restore from
the restic repositories.
"""

from pulumi import Input, Output, ResourceOptions
import pulumi_kubernetes as k8s

from .volume import RefVolumeProvisionResult
from .workflow import (
    BACKUP_VOLUME_PATH,
    CACHES_DIR,
    RESTIC_PASSWORD_FILENAME,
    SECRET_VOLUME_PATH,
    SILVERBULLET_DATA_VOLUME_PATH,
    SYNCTHING_CONFIG_VOLUME_PATH,
    SYNCTHING_DATA_VOLUME_PATH,
    VAULTWARDEN_DATA_VOLUME_PATH,
    backup_container_env,
)

NAME = "backup-debug"

ARCHIVE_VOLUME_PATH = "/data/archive"
ARCHIVE_S3_RESTIC_CACHE_DIR = f"{CACHES_DIR}/s3-archive"
ARCHIVE_RESTIC_PASSWORD_FILENAME = "archive-restic-repository-password"
ARCHIVE_RESTIC_PASSWORD_FILE = (
    f"{SECRET_VOLUME_PATH}/{ARCHIVE_RESTIC_PASSWORD_FILENAME}"
)


def _archive_s3_restic_repository(bucket_name: Input[str]) -> Output[str]:
    """
    Returns the restic path to the S3-hosted restic archive repository.
    """
    return Output.concat("s3:https://s3.amazonaws.com/", bucket_name, "/archive/restic")


def provision_backup_debug_deployment(
    namespace_name: Input[str],
    image: str,
    image_pull_secret: k8s.core.v1.Secret | None,
    bucket_name: Input[str],
    bucket_region: Input[str],
    local_backup_claim_name: Input[str],
    archive_claim_name: Input[str],
    ref_volumes: RefVolumeProvisionResult,
    k8s_opts: ResourceOptions,
) -> k8s.apps.v1.Deployment:
    """
    Provisions the backup debug deployment.

    The deployment has zero replicas until it is scaled up by hand:

        $ kubectl -n $NAMESPACE scale deployment/backup-debug --replicas=1
        $ kubectl -n $NAMESPACE exec -it deployment/backup-debug -- bash

    Inside the pod, the lrestic, rrestic, and arrestic commands run restic
    against the local, S3, and S3 archive repositories, and srclone runs rclone
    against S3.

    NOTE: Scale the deployment back down when finished. restic commands left
    running in the pod hold repository locks, which make the nightly backup's
    prune fail.
    """
    labels = {"service-name": NAME}

    def mount(name: str, path: str, read_only: bool) -> k8s.core.v1.VolumeMountArgs:
        return k8s.core.v1.VolumeMountArgs(
            name=name,
            mount_path=path,
            read_only=read_only,
        )

    def pvc_volume(name: str, claim_name: Input[str]) -> k8s.core.v1.VolumeArgs:
        return k8s.core.v1.VolumeArgs(
            name=name,
            persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                claim_name=claim_name,
            ),
        )

    debug_env: dict[str, Input[str]] = {
        "AWS_DEFAULT_REGION": bucket_region,
        "ARCHIVE_S3_RESTIC_REPOSITORY": _archive_s3_restic_repository(bucket_name),
        "ARCHIVE_S3_RESTIC_CACHE_DIR": ARCHIVE_S3_RESTIC_CACHE_DIR,
        "ARCHIVE_RESTIC_PASSWORD_FILE": ARCHIVE_RESTIC_PASSWORD_FILE,
    }
    env = [
        *backup_container_env(bucket_name),
        *[k8s.core.v1.EnvVarArgs(name=k, value=v) for k, v in debug_env.items()],
    ]

    image_pull_secrets = (
        [k8s.core.v1.LocalObjectReferenceArgs(name=image_pull_secret.metadata.name)]
        if image_pull_secret is not None
        else []
    )

    pod_spec = k8s.core.v1.PodSpecArgs(
        containers=[
            k8s.core.v1.ContainerArgs(
                name=NAME,
                image=image,
                # The image's tag is reused for each new build, so a node would
                # otherwise keep running whichever build it pulled first.
                image_pull_policy="Always",
                command=["sleep", "infinity"],
                env=env,
                volume_mounts=[
                    mount("archive", ARCHIVE_VOLUME_PATH, True),
                    mount("local-backup", BACKUP_VOLUME_PATH, False),
                    mount("syncthing-config", SYNCTHING_CONFIG_VOLUME_PATH, True),
                    mount("syncthing-data", SYNCTHING_DATA_VOLUME_PATH, True),
                    mount("silverbullet-data", SILVERBULLET_DATA_VOLUME_PATH, True),
                    mount("vaultwarden-data", VAULTWARDEN_DATA_VOLUME_PATH, True),
                    mount("secrets", SECRET_VOLUME_PATH, True),
                ],
            ),
        ],
        image_pull_secrets=image_pull_secrets,
        volumes=[
            pvc_volume("archive", archive_claim_name),
            pvc_volume("local-backup", local_backup_claim_name),
            pvc_volume("syncthing-config", ref_volumes.syncthing_config.pvc.name),
            pvc_volume("syncthing-data", ref_volumes.syncthing_data.pvc.name),
            pvc_volume("silverbullet-data", ref_volumes.silverbullet_data.pvc.name),
            pvc_volume("vaultwarden-data", ref_volumes.vaultwarden_data.pvc.name),
            k8s.core.v1.VolumeArgs(
                name="secrets",
                secret=k8s.core.v1.SecretVolumeSourceArgs(
                    secret_name="restic",
                    default_mode=0o400,
                    items=[
                        k8s.core.v1.KeyToPathArgs(
                            key="repository_password",
                            path=RESTIC_PASSWORD_FILENAME,
                        ),
                        k8s.core.v1.KeyToPathArgs(
                            key="archive_repository_password",
                            path=ARCHIVE_RESTIC_PASSWORD_FILENAME,
                        ),
                    ],
                ),
            ),
        ],
    )

    return k8s.apps.v1.Deployment(
        "backup_debug",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=namespace_name,
            name=NAME,
        ),
        spec=k8s.apps.v1.DeploymentSpecArgs(
            replicas=0,
            selector=k8s.meta.v1.LabelSelectorArgs(match_labels=labels),
            strategy=k8s.apps.v1.DeploymentStrategyArgs(type="Recreate"),
            template=k8s.core.v1.PodTemplateSpecArgs(
                metadata=k8s.meta.v1.ObjectMetaArgs(labels=labels),
                spec=pod_spec,
            ),
        ),
        # The deployment is scaled by hand, which an update must not undo.
        opts=k8s_opts.merge(ResourceOptions(ignore_changes=["spec.replicas"])),
    )
