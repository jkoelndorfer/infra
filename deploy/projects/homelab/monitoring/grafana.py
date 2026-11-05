"""
projects.homelab.monitoring.grafana
===================================

This module provisions Grafana [1], served through Traefik, with VictoriaMetrics
provisioned as its default data source.

Grafana also provisions each dashboard in `dashboards.DASHBOARDS` [2]. Provisioned
dashboards cannot be saved from the UI. To change one, change its function; a
dashboard edited in Grafana can be exported as JSON to see what to change.

[1]: https://grafana.com/docs/grafana/latest/setup-grafana/configure-docker/
[2]: https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import (
    ConfigMapVolumeSourceArgs,
    EnvVarArgs,
    EnvVarSourceArgs,
    SecretKeySelectorArgs,
)
import pulumi_random as random

from infralib import DeploymentContext

from ..kubernetes import (
    HomelabBackingVolumeID,
    HomelabContainerConfigMapVolumeArgs,
    HomelabContainerVolumeArgs,
    HomelabContainerVolumeProvisionedSource,
    HomelabHTTPSDeploymentIngressArgs,
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
    service_fqdn,
)
from .dashboards import DATASOURCE_UID, dashboard_files
from .victoriametrics import SCRAPE_INTERVAL, VictoriaMetricsResult

SERVICE_NAME = "grafana"
IMAGE = "grafana/grafana:13.2.4"
HTTP_PORT = 3000
ADMIN_USER = "admin"

BACKING_VOLUME: HomelabBackingVolumeID = "data0"
DATA_PATH = PurePosixPath("/var/lib/grafana")
DATASOURCES_PATH = PurePosixPath("/etc/grafana/provisioning/datasources")
DATASOURCES_FILE_NAME = "datasources.yml"
DASHBOARD_PROVIDERS_PATH = PurePosixPath("/etc/grafana/provisioning/dashboards")
DASHBOARD_PROVIDERS_FILE_NAME = "dashboards.yml"
DASHBOARDS_PATH = PurePosixPath("/etc/grafana/dashboards")
DASHBOARDS_FOLDER = "Homelab"


@dataclass
class GrafanaArgs:
    """
    Arguments for provisioning Grafana.
    """

    namespace: Output[str]
    victoriametrics: VictoriaMetricsResult


@dataclass
class GrafanaResult:
    """
    The result of provisioning Grafana.
    """

    deployment: HomelabKubernetesDeployment


def provision_grafana(
    dctx: DeploymentContext,
    args: GrafanaArgs,
    opts: ResourceOptions,
) -> GrafanaResult:
    """
    Provisions Grafana.
    """
    admin_password = random.RandomPassword(
        "grafana_admin_password",
        length=32,
        lower=True,
        upper=True,
        numeric=True,
        special=False,
        opts=ResourceOptions(provider=dctx.provider_factory.random_provider()),
    )

    # NOTE: Grafana applies the admin password only when it creates its database,
    # on the first start. Afterwards, this secret no longer controls the password;
    # change it in Grafana, or with `grafana cli admin reset-admin-password`. To
    # read the initial password:
    #
    #     $ kubectl -n $NAMESPACE get secret grafana-admin \
    #         -o jsonpath='{.data.password}' | base64 -d
    admin_secret = k8s.core.v1.Secret(
        "grafana_admin",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name="grafana-admin",
        ),
        string_data={"password": admin_password.result},
        opts=opts,
    )

    datasources = args.victoriametrics.url.apply(_datasources)

    # Grafana reads provisioning files at startup. Autonaming is verbatim, so a
    # content hash in the name is what rolls the pod on a change.
    datasources_config_map = k8s.core.v1.ConfigMap(
        "grafana_datasources",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=datasources.apply(
                lambda d: (
                    f"{SERVICE_NAME}-datasources-"
                    f"{hashlib.sha256(d.encode()).hexdigest()[:8]}"
                )
            ),
        ),
        data={DATASOURCES_FILE_NAME: datasources},
        opts=opts,
    )

    dashboard_providers_config_map = _hashed_config_map(
        "grafana_dashboard_providers",
        args.namespace,
        f"{SERVICE_NAME}-dashboard-providers",
        {DASHBOARD_PROVIDERS_FILE_NAME: _dashboard_providers()},
        opts,
    )
    dashboards_config_map = _hashed_config_map(
        "grafana_dashboards",
        args.namespace,
        f"{SERVICE_NAME}-dashboards",
        dashboard_files(dctx),
        opts,
    )

    env = {
        "GF_SERVER_ROOT_URL": f"https://{service_fqdn(dctx, SERVICE_NAME)}",
        "GF_SECURITY_ADMIN_USER": ADMIN_USER,
        "GF_SECURITY_COOKIE_SECURE": "true",
        "GF_USERS_ALLOW_SIGN_UP": "false",
        "GF_AUTH_ANONYMOUS_ENABLED": "false",
        "GF_ANALYTICS_REPORTING_ENABLED": "false",
        "GF_ANALYTICS_CHECK_FOR_UPDATES": "false",
        "GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES": "false",
        # Log to stdout only, so that logs are read with kubectl rather than
        # accumulating in the container.
        "GF_LOG_MODE": "console",
    }

    deployment = HomelabKubernetesDeployment(
        name="grafana",
        args=HomelabKubernetesDeploymentArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
            image=IMAGE,
            https_ingress=HomelabHTTPSDeploymentIngressArgs(
                container_port=HTTP_PORT,
            ),
            env=[
                *[EnvVarArgs(name=k, value=v) for k, v in env.items()],
                EnvVarArgs(
                    name="GF_SECURITY_ADMIN_PASSWORD",
                    value_from=EnvVarSourceArgs(
                        secret_key_ref=SecretKeySelectorArgs(
                            name=admin_secret.metadata["name"],
                            key="password",
                        ),
                    ),
                ),
            ],
            privilege_drop_mode="pod-exec",
            volumes=[
                HomelabContainerVolumeArgs(
                    name="data",
                    mount_path=str(DATA_PATH),
                    source=HomelabContainerVolumeProvisionedSource(
                        backing_volume=BACKING_VOLUME,
                        storage="5Gi",
                        access_modes=["ReadWriteOnce"],
                        mode="0700",
                    ),
                    read_only=False,
                ),
            ],
            config_map_volumes=[
                HomelabContainerConfigMapVolumeArgs(
                    name="datasources",
                    mount_path=str(DATASOURCES_PATH),
                    config_map=ConfigMapVolumeSourceArgs(
                        name=datasources_config_map.metadata["name"],
                        default_mode=0o444,
                    ),
                ),
                HomelabContainerConfigMapVolumeArgs(
                    name="dashboard-providers",
                    mount_path=str(DASHBOARD_PROVIDERS_PATH),
                    config_map=ConfigMapVolumeSourceArgs(
                        name=dashboard_providers_config_map.metadata["name"],
                        default_mode=0o444,
                    ),
                ),
                HomelabContainerConfigMapVolumeArgs(
                    name="dashboards",
                    mount_path=str(DASHBOARDS_PATH),
                    config_map=ConfigMapVolumeSourceArgs(
                        name=dashboards_config_map.metadata["name"],
                        default_mode=0o444,
                    ),
                ),
            ],
        ),
        dctx=dctx,
        opts=opts,
    )

    return GrafanaResult(deployment=deployment)


def _datasources(victoriametrics_url: str) -> str:
    """
    Returns the data source provisioning file [1].

    VictoriaMetrics implements the Prometheus query API, so Grafana's built-in
    Prometheus data source works with it, without installing a plugin.

    [1]: https://grafana.com/docs/grafana/latest/administration/provisioning/#data-sources
    """
    # YAML is a superset of JSON, so Grafana can read this as YAML.
    return json.dumps(
        {
            "apiVersion": 1,
            "datasources": [
                {
                    "name": "VictoriaMetrics",
                    "uid": DATASOURCE_UID,
                    "type": "prometheus",
                    "access": "proxy",
                    "url": victoriametrics_url,
                    "isDefault": True,
                    "editable": False,
                    # Lets $__rate_interval cover at least a few scrapes.
                    "jsonData": {"timeInterval": SCRAPE_INTERVAL},
                },
            ],
        },
        indent=2,
        sort_keys=True,
    )


def _hashed_config_map(
    resource_name: str,
    namespace: Output[str],
    name_prefix: str,
    data: dict[str, str],
    opts: ResourceOptions,
) -> k8s.core.v1.ConfigMap:
    """
    Returns a ConfigMap of provisioning files, named after a hash of its contents.

    Grafana reads provisioning files at startup. Autonaming is verbatim, so a
    content hash in the name is what rolls the pod on a change.
    """
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return k8s.core.v1.ConfigMap(
        resource_name,
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=namespace,
            name=f"{name_prefix}-{digest[:8]}",
        ),
        data=data,
        opts=opts,
    )


def _dashboard_providers() -> str:
    """
    Returns the dashboard provider provisioning file [1].

    [1]: https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards
    """
    return json.dumps(
        {
            "apiVersion": 1,
            "providers": [
                {
                    "name": "homelab",
                    "type": "file",
                    "folder": DASHBOARDS_FOLDER,
                    "disableDeletion": True,
                    "allowUiUpdates": False,
                    "options": {"path": str(DASHBOARDS_PATH)},
                },
            ],
        },
        indent=2,
        sort_keys=True,
    )
