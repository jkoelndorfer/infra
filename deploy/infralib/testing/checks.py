"""
infralib/testing/checks -- Rendered Stack Checks
================================================

This module contains checks that apply to every rendered stack. Mocks run no
provider code, so these enforce the provider and repository rules that would
otherwise only fail against real infrastructure.
"""

from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass
import re
from typing import Any

from .render import RecordedResource, Rendering

# Kubernetes object names. See:
# https://kubernetes.io/docs/concepts/overview/working-with-objects/names/
_RFC1123_SUBDOMAIN = re.compile(
    r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$"
)
_RFC1123_LABEL = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_K8S_NAME_MAX = 253

# Helm stores releases in Secrets whose names have a suffix, which limits releases
# to 53 characters. See https://helm.sh/docs/chart_template_guide/getting_started/.
_HELM_RELEASE_NAME_MAX = 53
_HELM_RELEASE_TYPE = "kubernetes:helm.sh/v3:Release"

_PROVIDER_TYPE_PREFIX = "pulumi:providers:"

# Text that only reaches an input by mistake: the message Pulumi leaves when an
# Output is formatted into a string, a Python None formatted into a string, and an
# f-string that is missing its prefix. Double braces and "${" are left alone,
# because Go templates and IAM policy variables use them.
_BROKEN_TEXT = re.compile(
    r"Calling __str__ on an Output"
    r"|<pulumi\.output\.Output"
    r"|\bNone\b"
    r"|(?<![{$%])\{[A-Za-z_][\w.]*\}(?!\})"
)

# Types whose `name` input does not need to be unique. A DNS name can hold many
# record types.
_NON_UNIQUE_NAME_TYPES = {
    "aws:route53/record:Record",
}


@dataclass(frozen=True)
class Finding:
    """
    A rule that a rendered resource breaks.
    """

    check: str
    urn: str
    message: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.urn}: {self.message}"


def _strings(value: Any) -> Iterator[str]:
    """
    Yields every string nested in the value.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _images(value: Any) -> Iterator[str]:
    """
    Yields every string under a key named "image" nested in the value.
    """
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "image" and isinstance(v, str):
                yield v
            else:
                yield from _images(v)
    elif isinstance(value, list):
        for v in value:
            yield from _images(v)


def _is_kubernetes_object(r: RecordedResource) -> bool:
    return r.type.startswith("kubernetes:") and r.type != _HELM_RELEASE_TYPE


def _metadata(r: RecordedResource) -> dict[str, Any]:
    metadata = r.inputs.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def check_duplicate_urns(rendering: Rendering) -> Iterator[Finding]:
    """
    The Pulumi engine rejects duplicate URNs, but the mock runtime accepts them.
    """
    counts = Counter(r.urn for r in rendering.resources)
    for urn, count in counts.items():
        if count > 1:
            yield Finding("duplicate-urn", urn, f"registered {count} times")


def check_explicit_providers(rendering: Rendering) -> Iterator[Finding]:
    """
    Default providers are disabled, so each resource needs an explicit provider.
    """
    for r in rendering.resources:
        if r.custom and not r.type.startswith(_PROVIDER_TYPE_PREFIX) and not r.provider:
            yield Finding("explicit-provider", r.urn, "resource has no provider")


def check_kubernetes_names(rendering: Rendering) -> Iterator[Finding]:
    """
    Kubernetes and Helm reject invalid names only when they are applied. Without an
    explicit name, a name is derived from the logical name, which may be invalid.
    """
    for r in rendering.resources:
        if r.type == _HELM_RELEASE_TYPE:
            name = r.inputs.get("name") or r.name
            if len(name) > _HELM_RELEASE_NAME_MAX or not _RFC1123_LABEL.match(name):
                yield Finding(
                    "kubernetes-name", r.urn, f"invalid Helm release name: {name!r}"
                )
        elif _is_kubernetes_object(r):
            name = _metadata(r).get("name") or r.name
            if len(name) > _K8S_NAME_MAX or not _RFC1123_SUBDOMAIN.match(name):
                yield Finding(
                    "kubernetes-name", r.urn, f"invalid object name: {name!r}"
                )


def check_unique_names(rendering: Rendering) -> Iterator[Finding]:
    """
    Autonaming is verbatim, so two resources with the same physical name collide.
    """
    seen: dict[tuple[Any, ...], str] = {}
    for r in rendering.resources:
        key: tuple[Any, ...]
        if _is_kubernetes_object(r):
            metadata = _metadata(r)
            name = metadata.get("name") or r.name
            key = (r.type, r.provider, metadata.get("namespace"), name)
        elif (
            isinstance(r.inputs.get("name"), str)
            and r.type not in _NON_UNIQUE_NAME_TYPES
        ):
            key = (r.type, r.provider, r.inputs["name"])
        else:
            continue
        if key in seen:
            yield Finding(
                "unique-name", r.urn, f"same physical name as {seen[key]}: {key[-1]!r}"
            )
        else:
            seen[key] = r.urn


def check_pinned_versions(rendering: Rendering) -> Iterator[Finding]:
    """
    Container image tags and chart versions must be pinned.
    """
    for r in rendering.resources:
        if r.type == _HELM_RELEASE_TYPE:
            chart = str(r.inputs.get("chart", ""))
            if "@sha256:" not in chart and not r.inputs.get("version"):
                yield Finding("pinned-version", r.urn, f"unpinned chart: {chart!r}")
        if not r.type.startswith("kubernetes:"):
            continue
        for image in _images(r.inputs):
            # A "{{" is an Argo template, which is resolved when a workflow runs.
            if "@sha256:" in image or "{{" in image:
                continue
            tag = image.rsplit("/", 1)[-1].partition(":")[2]
            if tag in ("", "latest"):
                yield Finding("pinned-version", r.urn, f"unpinned image: {image!r}")


def check_broken_text(rendering: Rendering) -> Iterator[Finding]:
    """
    Formatting mistakes render without error, and then deploy.
    """
    for r in rendering.resources:
        for s in _strings(r.inputs):
            match = _BROKEN_TEXT.search(s)
            if match is not None:
                yield Finding(
                    "broken-text", r.urn, f"{match.group(0)!r} in input {s[:120]!r}"
                )


def check_imports(rendering: Rendering) -> Iterator[Finding]:
    """
    Pulumi fails an import once a resource has been deleted, so a leftover import
    prevents a stack from being rebuilt.
    """
    for r in rendering.resources:
        if r.import_id is not None:
            yield Finding(
                "leftover-import",
                r.urn,
                f"imports {r.import_id!r}; remove import_ once it has been deployed",
            )


CHECKS: list[Callable[[Rendering], Iterator[Finding]]] = [
    check_broken_text,
    check_duplicate_urns,
    check_explicit_providers,
    check_imports,
    check_kubernetes_names,
    check_pinned_versions,
    check_unique_names,
]


def run_checks(rendering: Rendering) -> list[Finding]:
    """
    Returns the findings of every check for the rendering.
    """
    return [finding for check in CHECKS for finding in check(rendering)]
