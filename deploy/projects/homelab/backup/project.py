"""
projects.homelab.backup.project
===============================

This module contains the InfrastructureProject for backups.
"""

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

from pulumi import ResourceOptions

from ...aws.accounts import AWSAccountsProject
from ..argo_workflows import HomelabArgoWorkflowsProject
from ..ctr_registry import (
    HomelabContainerRegistryProject,
    HomelabContainerRegistryImagePullSecretProvider,
)
from ..kubernetes import HomelabBackingVolumeID, namespace
from ..syncthing import HomelabSyncthingProject
from ..vaultwarden import HomelabVaultwardenProject

from .kserv import provision_kserv_backup
from .kubernetes import provision_kubernetes_sa
from .s3 import provision_backup_bucket
from .iam import provision_iam
from .volume import provision_local_backup_volume, provision_ref_volumes
from .workflow import provision_backup_workflow


class HomelabBackupProject(InfrastructureProject):
    name = "homelab.backup"
    backing_volume: HomelabBackingVolumeID = "data0"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        prod = DeploymentTarget(Environment.PROD, None)
        return [
            AWSAccountsProject.stack(target),
            HomelabArgoWorkflowsProject.stack(prod),
            HomelabContainerRegistryProject.stack(prod),
            HomelabSyncthingProject.stack(target),
            HomelabVaultwardenProject.stack(target),
        ]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(e, None) for e in [Environment.DEV, Environment.PROD]]

    @property
    def _backup_image(self) -> str:
        registry_fqdn = HomelabContainerRegistryProject.registry_fqdn(
            dctx=self.dctx,
            access="ro",
            target=DeploymentTarget(Environment.PROD, None),
        )
        return f"{registry_fqdn}/backupjob:{self.dctx.target.environment}"

    def _init_providers(self) -> None:
        _, self.aws_provider = AWSAccountsProject.lookup_account(
            self.dctx,
            "backup",
            self.dctx.target.environment,
        )
        self.k8s_provider = self.dctx.provider_factory.kubernetes_provider()
        self.aws_ropts = ResourceOptions(provider=self.aws_provider)
        self.k8s_ropts = ResourceOptions(provider=self.k8s_provider)
        self.ip_secret_provider = HomelabContainerRegistryImagePullSecretProvider()

    def pulumi_program(self) -> None:
        self._init_providers()
        ns_name, ns = namespace(
            "namespace",
            self.dctx.target.environment,
            "backup",
            opts=self.k8s_ropts,
        )
        image_pull_secret = self.ip_secret_provider.secret(
            "internal",
            self.dctx,
            ns_name,
            self._backup_image,
        )
        bucket = provision_backup_bucket(
            dctx=self.dctx,
            aws_opts=self.aws_ropts,
        )
        iam_provisioning_result = provision_iam(
            dctx=self.dctx,
            backup_bucket_arn=bucket.arn,
            aws_opts=self.aws_ropts,
        )
        provision_kserv_backup(
            dctx=self.dctx,
            namespace_name=ns_name,
            iam_provisioning_result=iam_provisioning_result,
            aws_opts=self.aws_ropts,
            k8s_opts=self.k8s_ropts,
        )
        local_backup_volume = provision_local_backup_volume(
            dctx=self.dctx,
            namespace=ns_name,
            backing_volume=self.backing_volume,
            k8s_opts=self.k8s_ropts,
        )
        ref_volume_provisioning_result = provision_ref_volumes(
            dctx=self.dctx,
            namespace=ns_name,
            k8s_opts=self.k8s_ropts,
        )
        service_account = provision_kubernetes_sa(
            dctx=self.dctx,
            namespace_name=ns_name,
            k8s_opts=self.k8s_ropts,
        )
        provision_backup_workflow(
            dctx=self.dctx,
            namespace_name=ns_name,
            image=self._backup_image,
            image_pull_secret=image_pull_secret,
            service_account=service_account,
            bucket_name=bucket.bucket,
            local_backup_claim_name=local_backup_volume.pvc.name,
            ref_volumes=ref_volume_provisioning_result,
            k8s_opts=self.k8s_ropts,
        )
