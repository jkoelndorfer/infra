"""
projects.homelab.unifi.database
===============================

This module provisions the MongoDB database that the UniFi Network Application
stores its data in [1].

The database's users are created by an init script that the MongoDB image runs
when it starts with an empty data directory [2]. The script is the one that the
UniFi Network Application image documents, unmodified.

[1]: https://github.com/linuxserver/docker-unifi-network-application#setting-up-your-external-database
[2]: https://hub.docker.com/_/mongo#initializing-a-fresh-instance
"""

from dataclasses import dataclass
from pathlib import PurePosixPath

from pulumi import Output, ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import (
    ConfigMapVolumeSourceArgs,
    ContainerPortArgs,
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
    HomelabKubernetesDeployment,
    HomelabKubernetesDeploymentArgs,
)

SERVICE_NAME = "unifi-db"

# NOTE: The UniFi Network Application supports a limited range of MongoDB
# versions; check its documentation before changing the major version. MongoDB
# also cannot skip major versions when upgrading an existing data directory.
IMAGE = "mongo:8.0.34"

PORT = 27017
BACKING_VOLUME: HomelabBackingVolumeID = "data0"
DATA_PATH = PurePosixPath("/data/db")
INIT_PATH = PurePosixPath("/docker-entrypoint-initdb.d")
INIT_FILE_NAME = "init-mongo.sh"

ROOT_USER = "root"
USER = "unifi"
DBNAME = "unifi"
AUTHSOURCE = "admin"

PASSWORD_KEY = "password"
ROOT_PASSWORD_KEY = "root-password"

# The init script that the UniFi Network Application image documents [1]. It
# reads its parameters from the environment of the MongoDB container.
INIT_SCRIPT = """\
#!/bin/bash

if which mongosh > /dev/null 2>&1; then
  mongo_init_bin='mongosh'
else
  mongo_init_bin='mongo'
fi
"${mongo_init_bin}" <<EOF
use ${MONGO_AUTHSOURCE}
db.auth("${MONGO_INITDB_ROOT_USERNAME}", "${MONGO_INITDB_ROOT_PASSWORD}")
db.createUser({
  user: "${MONGO_USER}",
  pwd: "${MONGO_PASS}",
  roles: [
    "clusterMonitor",
    { db: "${MONGO_DBNAME}", role: "dbOwner" },
    { db: "${MONGO_DBNAME}_stat", role: "dbOwner" },
    { db: "${MONGO_DBNAME}_audit", role: "dbOwner" },
    { db: "${MONGO_DBNAME}_restore", role: "dbOwner" }
  ]
})
EOF
"""


@dataclass
class UnifiDatabaseArgs:
    """
    Arguments for provisioning the UniFi database.
    """

    namespace: Output[str]

    client_label_selector: k8s.meta.v1.LabelSelectorArgs
    """
    Selects the pods permitted to connect to the database.
    """


@dataclass
class UnifiDatabaseResult:
    """
    The result of provisioning the UniFi database.
    """

    deployment: HomelabKubernetesDeployment

    client_env: list[EnvVarArgs]
    """
    Environment variables that connect the UniFi Network Application to the
    database.
    """


def provision_database(
    dctx: DeploymentContext,
    args: UnifiDatabaseArgs,
    opts: ResourceOptions,
) -> UnifiDatabaseResult:
    """
    Provisions the UniFi database.
    """
    random_opts = ResourceOptions(provider=dctx.provider_factory.random_provider())

    # Special characters would have to be URL-encoded in the UniFi Network
    # Application's connection settings, so passwords are alphanumeric.
    passwords = {
        key: random.RandomPassword(
            f"unifi_db_{key.replace('-', '_')}",
            length=32,
            lower=True,
            upper=True,
            numeric=True,
            special=False,
            opts=random_opts,
        )
        for key in (PASSWORD_KEY, ROOT_PASSWORD_KEY)
    }

    # NOTE: MongoDB applies these passwords only when it initializes an empty
    # data directory. Afterwards, changing this secret does not change them.
    secret = k8s.core.v1.Secret(
        "unifi_db_credentials",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=f"{SERVICE_NAME}-credentials",
        ),
        string_data={k: v.result for k, v in passwords.items()},
        opts=opts,
    )

    def secret_env(name: str, key: str) -> EnvVarArgs:
        return EnvVarArgs(
            name=name,
            value_from=EnvVarSourceArgs(
                secret_key_ref=SecretKeySelectorArgs(
                    name=secret.metadata["name"],
                    key=key,
                ),
            ),
        )

    init_config_map = k8s.core.v1.ConfigMap(
        "unifi_db_init",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=f"{SERVICE_NAME}-init",
        ),
        data={INIT_FILE_NAME: INIT_SCRIPT},
        opts=opts,
    )

    env = {
        "MONGO_INITDB_ROOT_USERNAME": ROOT_USER,
        "MONGO_USER": USER,
        "MONGO_DBNAME": DBNAME,
        "MONGO_AUTHSOURCE": AUTHSOURCE,
        # The container runs as a user without a home directory, and the init
        # script's mongosh writes its state there.
        "HOME": "/tmp",
    }

    deployment = HomelabKubernetesDeployment(
        name="unifi_db",
        args=HomelabKubernetesDeploymentArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
            image=IMAGE,
            env=[
                *[EnvVarArgs(name=k, value=v) for k, v in env.items()],
                secret_env("MONGO_INITDB_ROOT_PASSWORD", ROOT_PASSWORD_KEY),
                secret_env("MONGO_PASS", PASSWORD_KEY),
            ],
            ports=[
                ContainerPortArgs(
                    container_port=PORT,
                    name="mongodb",
                    protocol="TCP",
                ),
            ],
            # The image's entrypoint runs as whichever user starts it, and only
            # switches users when started as root.
            privilege_drop_mode="pod-exec",
            volumes=[
                HomelabContainerVolumeArgs(
                    name="db",
                    mount_path=str(DATA_PATH),
                    source=HomelabContainerVolumeProvisionedSource(
                        backing_volume=BACKING_VOLUME,
                        storage="10Gi",
                        access_modes=["ReadWriteOnce"],
                        mode="0700",
                    ),
                    read_only=False,
                ),
            ],
            config_map_volumes=[
                HomelabContainerConfigMapVolumeArgs(
                    name="init",
                    mount_path=str(INIT_PATH),
                    config_map=ConfigMapVolumeSourceArgs(
                        name=init_config_map.metadata["name"],
                        default_mode=0o444,
                    ),
                ),
            ],
        ),
        dctx=dctx,
        opts=opts,
    )

    service = k8s.core.v1.Service(
        "unifi_db_service",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=SERVICE_NAME,
        ),
        spec=k8s.core.v1.ServiceSpecArgs(
            type=k8s.core.v1.ServiceSpecType.CLUSTER_IP,
            selector=deployment.service_label,
            ports=[
                k8s.core.v1.ServicePortArgs(
                    port=PORT,
                    target_port="mongodb",
                    name="mongodb",
                ),
            ],
        ),
        opts=opts,
    )

    k8s.networking.v1.NetworkPolicy(
        "unifi_db_clients",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            namespace=args.namespace,
            name=f"{SERVICE_NAME}-clients",
        ),
        spec=k8s.networking.v1.NetworkPolicySpecArgs(
            pod_selector=deployment.label_selector,
            policy_types=["Ingress"],
            ingress=[
                k8s.networking.v1.NetworkPolicyIngressRuleArgs(
                    from_=[
                        k8s.networking.v1.NetworkPolicyPeerArgs(
                            pod_selector=args.client_label_selector,
                        ),
                    ],
                    ports=[
                        k8s.networking.v1.NetworkPolicyPortArgs(
                            port="mongodb",
                            protocol="TCP",
                        ),
                    ],
                ),
            ],
        ),
        opts=opts,
    )

    client_env = [
        EnvVarArgs(name="MONGO_HOST", value=service.metadata["name"]),
        EnvVarArgs(name="MONGO_PORT", value=str(PORT)),
        EnvVarArgs(name="MONGO_USER", value=USER),
        EnvVarArgs(name="MONGO_DBNAME", value=DBNAME),
        EnvVarArgs(name="MONGO_AUTHSOURCE", value=AUTHSOURCE),
        secret_env("MONGO_PASS", PASSWORD_KEY),
    ]
    return UnifiDatabaseResult(deployment=deployment, client_env=client_env)
