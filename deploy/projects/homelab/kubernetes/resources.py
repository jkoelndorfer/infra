"""
projects.homelab.kubernetes.resources
=====================================

This module contains helper functions to define Kubernetes resources that
comply with homelab standards.
"""

from typing import Any, Mapping, Tuple

from infralib import Environment

from pulumi import Input, Output, ResourceOptions
import pulumi_kubernetes as k8s


def namespace(
    resource_name: str,
    env: Environment,
    name: str,
    opts: ResourceOptions,
) -> Tuple[Output[str], k8s.core.v1.Namespace]:
    """
    Creates a Kubernetes namespace with the given environment and name.
    """
    ns_name = f"{env}-{name}"

    # Kubernetes automatically sets the kubernetes.io/metadata.name
    # label and configures a spec.finalizer on each created namespace.
    opts = opts.merge(
        ResourceOptions(
            ignore_changes=[
                'metadata.labels["kubernetes.io/metadata.name"]',
                "spec",
            ],
        )
    )
    ns = k8s.core.v1.Namespace(
        resource_name,
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=ns_name,
            labels={
                "local/env": env,
                "local/name": name,
            },
        ),
        opts=opts,
    )
    ns_name_output: Output[str] = ns.metadata["name"]

    return (ns_name_output, ns)


def helm_release(
    resource_name: str,
    oci_uri: Input[str],
    version: Input[str],
    sha256: Input[str],
    namespace: Input[str],
    values: Input[Mapping[str, Any]],
    opts: ResourceOptions,
) -> k8s.helm.v3.Release:
    # NOTE: sha256 is calculated from the chart's manifest, not the tarball
    # that is pulled down.
    #
    # To calculate the digest, run:
    #
    #     $ helm pull $oci_uri --version $version
    #
    # Helm will print the digest.
    return k8s.helm.v3.Release(
        resource_name,
        chart=f"{oci_uri}:{version}@sha256:{sha256}",
        namespace=namespace,
        values=values,
        opts=opts,
    )
