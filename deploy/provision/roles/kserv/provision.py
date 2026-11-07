"""
provision/roles/kserv/provision -- kserv Provisioning
=====================================================

This module contains provisioning logic for the kserv role.
"""

from pathlib import Path, PurePosixPath
from typing import Any

from pyinfra.api.operation import OperationMeta
from pyinfra.context import host
from pyinfra.operations import files, server, systemd
from pyinfra.operations.util import any_changed

from infralib import InfrastructureConfiguration
from infralib.config.homelab import HomelabNetworking
from infralib.error import InvalidConfigurationError

_FILES = Path(__file__).parent / "files"

_JINJA_ENV_KWARGS: dict[str, Any] = {"lstrip_blocks": True, "trim_blocks": True}

# The address of the cluster's DNS service, as an offset into the service network.
# NOTE: Pods get this address when they are created, so changing it means
# recreating every pod.
_CLUSTER_DNS_OFFSET = 12


def provision(config: InfrastructureConfiguration) -> None:
    """
    Provisions the Kubernetes host.
    """
    _provision_kernel()
    _provision_boot()
    _provision_network(config.homelab.network)
    _provision_sshd()
    _provision_k3s(config.homelab.network, _data0_volume_path())


def _data0_volume_path() -> PurePosixPath:
    """
    Returns where the host mounts data0, from the inventory's data0_volume_path.
    """
    value = host.data.get("data0_volume_path")
    if not isinstance(value, str) or not PurePosixPath(value).is_absolute():
        raise InvalidConfigurationError(
            f"{host.name}: data0_volume_path must be an absolute path, not {value!r}"
        )
    return PurePosixPath(value)


def _template(name: str, src: str, dest: str, **data: Any) -> OperationMeta:
    """
    Deploys a template from the role's files directory, owned by root.
    """
    return files.template(
        name=f"deploy {name}",
        src=str(_FILES / src),
        dest=dest,
        user="root",
        group="root",
        mode="0644",
        jinja_env_kwargs=_JINJA_ENV_KWARGS,
        _sudo=True,
        **data,
    )


def _put(name: str, src: str, dest: str, mode: str = "0644") -> OperationMeta:
    """
    Deploys a file from the role's files directory, owned by root.
    """
    return files.put(
        name=f"deploy {name}",
        src=str(_FILES / src),
        dest=dest,
        user="root",
        group="root",
        mode=mode,
        _sudo=True,
    )


def _provision_kernel() -> None:
    modules = _put(
        "k3s kernel modules", "modules-load.d/k3s.conf", "/etc/modules-load.d/k3s.conf"
    )
    systemd.service(
        name="load kernel modules",
        service="systemd-modules-load.service",
        running=True,
        restarted=True,
        _if=modules.did_change,
        _sudo=True,
    )

    # NOTE: This comes after the modules, because the net.bridge settings do not
    # exist until br_netfilter is loaded.
    sysctl = _put(
        "k3s sysctl settings", "sysctl.d/90-k3s.conf", "/etc/sysctl.d/90-k3s.conf"
    )
    server.shell(
        name="apply sysctl settings",
        commands=["sysctl --system"],
        _if=sysctl.did_change,
        _sudo=True,
    )


def _provision_boot() -> None:
    # NOTE: The sd-encrypt hook copies the /etc/crypttab entries that have
    # x-initrd.attach into the initramfs, so a change to crypttab needs a rebuild.
    crypttab = _put("crypttab", "crypttab", "/etc/crypttab", mode="0600")

    mkinitcpio = _put(
        "mkinitcpio configuration", "mkinitcpio.conf", "/etc/mkinitcpio.conf"
    )
    server.shell(
        name="rebuild initramfs",
        commands=["mkinitcpio -P"],
        _if=any_changed(crypttab, mkinitcpio),
        _sudo=True,
    )


def _provision_network(networking: HomelabNetworking) -> None:
    network = _template(
        "primary network configuration",
        "primary.network.j2",
        "/etc/systemd/network/primary.network",
        mac=networking.kubernetes_host_assignment.mac,
    )
    server.shell(
        name="reload network configuration",
        commands=["networkctl reload"],
        _if=network.did_change,
        _sudo=True,
    )


def _provision_sshd() -> None:
    dropin = _put(
        "sshd configuration",
        "sshd_config.d/10-kserv.conf",
        "/etc/ssh/sshd_config.d/10-kserv.conf",
    )
    main = _put("sshd main configuration", "sshd_config", "/etc/ssh/sshd_config")

    # NOTE: The check fails the deployment before the reload, so a bad
    # configuration does not reach the running sshd. It is still on disk, though,
    # and must be fixed before sshd next restarts.
    server.shell(
        name="check sshd configuration",
        commands=["sshd -t"],
        _if=any_changed(dropin, main),
        _sudo=True,
    )
    systemd.service(
        name="reload sshd",
        service="sshd.service",
        running=True,
        reloaded=True,
        _if=any_changed(dropin, main),
        _sudo=True,
    )


def _provision_k3s(networking: HomelabNetworking, data0: PurePosixPath) -> None:
    node_name = networking.kubernetes_host_assignment.name
    networks = networking.networks
    service_network = networks.kube_service.ipv4_network

    # NOTE: Quadlet generates k3s.service from this file, so the unit cannot be
    # enabled; its [Install] section takes effect at the daemon reload instead.
    # Restarting k3s restarts every pod.
    container = _template(
        "k3s container",
        "k3s.container.j2",
        "/etc/containers/systemd/k3s.container",
        data0=data0,
        node_name=node_name,
        cluster_cidr=networks.kube_cluster.ipv4_network,
        service_cidr=service_network,
        cluster_dns=service_network[_CLUSTER_DNS_OFFSET],
    )
    metadata = _template(
        "k3s node metadata unit",
        "k3s-node-metadata.service.j2",
        "/etc/systemd/system/k3s-node-metadata.service",
        node_name=node_name,
        kubeconfig=data0 / "k3s" / "kubeconfig",
        volume_path=data0 / "services",
    )

    systemd.daemon_reload(
        name="reload systemd units",
        _if=any_changed(container, metadata),
        _sudo=True,
    )
    systemd.service(
        name="restart k3s",
        service="k3s.service",
        running=True,
        restarted=True,
        _if=container.did_change,
        _sudo=True,
    )
    systemd.service(
        name="enable k3s node metadata unit",
        service="k3s-node-metadata.service",
        enabled=True,
        _sudo=True,
    )
    systemd.service(
        name="apply k3s node metadata",
        service="k3s-node-metadata.service",
        running=True,
        restarted=True,
        _if=metadata.did_change,
        _sudo=True,
    )
