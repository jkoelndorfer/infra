"""
tests/infralib/testing/test_checks -- Rendered Stack Check Tests
================================================================

This module contains tests for the checks that apply to rendered stacks. Several
cases are bugs that reached a real deployment, or a human reviewer, before these
checks existed.
"""

from typing import Any

import pytest

from infralib import DeploymentTarget, Environment, InfrastructureStack
from infralib.testing import RecordedResource, Rendering, run_checks
from infralib.testing.checks import (
    check_broken_text,
    check_duplicate_urns,
    check_explicit_providers,
    check_imports,
    check_kubernetes_names,
    check_pinned_versions,
    check_unique_names,
)
from projects.noop import NoopProject

STACK: InfrastructureStack = NoopProject.stack(DeploymentTarget(Environment.PROD, None))
PROVIDER = "urn:provider::id"
RELEASE = "kubernetes:helm.sh/v3:Release"
SECRET = "kubernetes:core/v1:Secret"
DEPLOYMENT = "kubernetes:apps/v1:Deployment"


def resource(
    type_: str = "aws:s3/bucket:Bucket",
    name: str = "resource",
    inputs: dict[str, Any] | None = None,
    urn: str | None = None,
    provider: str | None = PROVIDER,
    import_id: str | None = None,
    custom: bool = True,
) -> RecordedResource:
    return RecordedResource(
        urn=urn if urn is not None else f"urn:{type_}::{name}",
        type=type_,
        name=name,
        inputs=inputs if inputs is not None else {},
        provider=provider,
        import_id=import_id,
        custom=custom,
    )


def rendering(*resources: RecordedResource) -> Rendering:
    return Rendering(STACK, resources=list(resources))


def test_clean_rendering_has_no_findings() -> None:
    assert run_checks(rendering(resource())) == []


def test_finding_includes_check_and_urn() -> None:
    findings = run_checks(rendering(resource(provider=None)))

    assert str(findings[0]).startswith("[explicit-provider] urn:")


def test_duplicate_urns() -> None:
    r = rendering(resource(urn="urn:same"), resource(urn="urn:same"))

    assert [f.check for f in check_duplicate_urns(r)] == ["duplicate-urn"]


@pytest.mark.parametrize(
    "r,expected",
    [
        (resource(provider=None), 1),
        (resource(provider=PROVIDER), 0),
        (resource("pulumi:providers:aws", provider=None), 0),
        (resource("my:component:Thing", provider=None, custom=False), 0),
    ],
)
def test_explicit_providers(r: RecordedResource, expected: int) -> None:
    assert len(list(check_explicit_providers(rendering(r)))) == expected


@pytest.mark.parametrize(
    "r,expected",
    [
        # Helm rejected the name derived from this logical name during a real run.
        (resource(RELEASE, "argo_workflows"), 1),
        (resource(RELEASE, "argo_workflows", {"name": "argo-workflows"}), 0),
        (resource(RELEASE, "x", {"name": "a" * 54}), 1),
        (resource(SECRET, "my_secret"), 1),
        (resource(SECRET, "my_secret", {"metadata": {"name": "my-secret"}}), 0),
        (resource(SECRET, "x", {"metadata": {"name": "Upper"}}), 1),
        (resource(SECRET, "x", {"metadata": {"name": "a.b-c"}}), 0),
        (resource(SECRET, "x", {"metadata": {"name": "a" * 254}}), 1),
    ],
)
def test_kubernetes_names(r: RecordedResource, expected: int) -> None:
    assert len(list(check_kubernetes_names(rendering(r)))) == expected


def test_unique_kubernetes_names_consider_namespace() -> None:
    same_namespace = rendering(
        resource(SECRET, "a", {"metadata": {"name": "x", "namespace": "n"}}),
        resource(SECRET, "b", {"metadata": {"name": "x", "namespace": "n"}}),
    )
    other_namespace = rendering(
        resource(SECRET, "a", {"metadata": {"name": "x", "namespace": "n"}}),
        resource(SECRET, "b", {"metadata": {"name": "x", "namespace": "m"}}),
    )

    assert len(list(check_unique_names(same_namespace))) == 1
    assert list(check_unique_names(other_namespace)) == []


def test_unique_names_for_cloud_resources() -> None:
    bucket = "aws:s3/bucket:Bucket"
    record = "aws:route53/record:Record"

    assert (
        len(
            list(
                check_unique_names(
                    rendering(
                        resource(bucket, "a", {"name": "x"}),
                        resource(bucket, "b", {"name": "x"}),
                    )
                )
            )
        )
        == 1
    )
    assert (
        list(
            check_unique_names(
                rendering(
                    resource(record, "a", {"name": "x"}),
                    resource(record, "b", {"name": "x"}),
                )
            )
        )
        == []
    )
    assert (
        list(
            check_unique_names(rendering(resource(bucket, "a"), resource(bucket, "b")))
        )
        == []
    )


@pytest.mark.parametrize(
    "r,expected",
    [
        (resource(RELEASE, inputs={"chart": "oci://x/y"}), 1),
        (resource(RELEASE, inputs={"chart": "oci://x/y", "version": "1.0"}), 0),
        (resource(RELEASE, inputs={"chart": "oci://x/y:1@sha256:abc"}), 0),
        (resource(DEPLOYMENT, inputs={"spec": [{"image": "nginx"}]}), 1),
        (resource(DEPLOYMENT, inputs={"spec": {"image": "nginx:latest"}}), 1),
        (resource(DEPLOYMENT, inputs={"spec": {"image": "reg:5000/nginx"}}), 1),
        (resource(DEPLOYMENT, inputs={"spec": {"image": "reg:5000/nginx:1.2"}}), 0),
        (resource(DEPLOYMENT, inputs={"spec": {"image": "nginx@sha256:abc"}}), 0),
        (resource(DEPLOYMENT, inputs={"spec": {"image": "{{ params.image }}"}}), 0),
        (resource("aws:x/y:Z", inputs={"image": "nginx"}), 0),
    ],
)
def test_pinned_versions(r: RecordedResource, expected: int) -> None:
    assert len(list(check_pinned_versions(rendering(r)))) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        # A missing f-string prefix once reached a notification message.
        ("hello {name}", 1),
        ("hello {self.name}", 1),
        ("arn:aws:s3:::None/key", 1),
        ("Calling __str__ on an Output[T] is not supported.", 1),
        ("<pulumi.output.Output object at 0x7f>", 1),
        ("{{ workflow.parameters.image }}", 0),
        ("arn:aws:iam::${aws:username}", 0),
        ('{"json": "document"}', 0),
        ("Nonexistent is a word", 0),
    ],
)
def test_broken_text(text: str, expected: int) -> None:
    r = rendering(resource(inputs={"nested": [{"value": text}], "number": 1}))

    assert len(list(check_broken_text(r))) == expected


def test_imports_are_not_left_in_place() -> None:
    assert [
        f.check for f in check_imports(rendering(resource(import_id="existing")))
    ] == ["leftover-import"]
    assert list(check_imports(rendering(resource()))) == []
