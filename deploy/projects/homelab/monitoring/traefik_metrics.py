"""
projects.homelab.monitoring.traefik_metrics
===========================================

This module derives labels from Traefik's metrics, so that dashboards can group
requests by Kubernetes namespace, deployment, and status class.

Traefik labels each request metric with the Traefik service that handled it. With
safe naming [1], the Kubernetes CRD provider joins the parts of each service name
with `_`, which Kubernetes names cannot contain, so the parts split unambiguously.
The first part is the namespace, and the second is the name of an object in it. For
the service of a route of an IngressRoute, the object is the IngressRoute:

    prod-vaultwarden_vaultwarden-https-ingress_0_lb@kubernetescrd

[1]: https://doc.traefik.io/traefik/reference/install-configuration/providers/kubernetes/kubernetes-crd/#safenaming
"""

from typing import Any

NAMESPACE_LABEL = "namespace"
DEPLOYMENT_LABEL = "deployment"
CODE_CLASS_LABEL = "code_class"

OTHER_NAMESPACE = "(other)"
"""
The namespace label value for Traefik services that do not come from the Kubernetes
CRD provider, such as Traefik's own api@internal.
"""

OTHER_CODE_CLASS = "(other)"
"""
The code_class label value for codes that are not HTTP statuses. Traefik reports
the code 0 for a request that got no response status, such as when the client
disconnects first.
"""

# HomelabKubernetesDeployment names its IngressRoute `${DEPLOYMENT}-https-ingress`,
# and its Kubernetes Service `${DEPLOYMENT}-http`. The number of further parts
# depends on the kind of service.
_KUBERNETES_CRD_SERVICE = (
    "([^_]+)_([^_]+?)(?:-https-ingress|-http)?(?:_[^_]+)*@kubernetescrd"
)


def traefik_metric_relabel_configs() -> list[dict[str, Any]]:
    """
    Returns metric relabeling rules for a Traefik scrape job.

    The rules add these labels:

    - namespace and deployment, to each sample that has a service label. Other
      services get the namespace OTHER_NAMESPACE, and their service label as the
      deployment.
    - code_class, such as 2xx, to each sample that has a code label. Codes that are
      not HTTP statuses get OTHER_CODE_CLASS.

    VictoriaMetrics applies rules in order and anchors each regex, so later rules
    override earlier ones.
    """
    return [
        _service_rule("(.+)", NAMESPACE_LABEL, OTHER_NAMESPACE),
        _service_rule("(.+)", DEPLOYMENT_LABEL, "$1"),
        _service_rule(_KUBERNETES_CRD_SERVICE, NAMESPACE_LABEL, "$1"),
        _service_rule(_KUBERNETES_CRD_SERVICE, DEPLOYMENT_LABEL, "$2"),
        _code_rule("(.+)", OTHER_CODE_CLASS),
        _code_rule("([1-5])[0-9][0-9]", "${1}xx"),
    ]


def _code_rule(regex: str, replacement: str) -> dict[str, Any]:
    return {
        "action": "replace",
        "source_labels": ["code"],
        "regex": regex,
        "target_label": CODE_CLASS_LABEL,
        "replacement": replacement,
    }


def _service_rule(regex: str, target_label: str, replacement: str) -> dict[str, Any]:
    return {
        "action": "replace",
        "source_labels": ["service"],
        "regex": regex,
        "target_label": target_label,
        "replacement": replacement,
    }
