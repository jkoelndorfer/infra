"""
tests/infralib/testing/test_render -- Offline Rendering Tests
=============================================================

This module contains tests for rendering projects against the mock runtime.
"""

import asyncio
from base64 import b64decode
import json

import kubernetes
import pulumi
from pulumi import ResourceOptions
import pulumi_aws as aws
import pulumi_kubernetes as k8s
import pulumi_random as random
import pytest
import yaml

from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)
from infralib.error import UndeclaredDependencyError
from infralib.testing import (
    FakeKubernetesClient,
    MockProviderFactory,
    RecordedResource,
    Rendering,
    render,
    render_with_dependencies,
    render_yaml,
)

TARGET = DeploymentTarget(Environment.TEST, None)
PENDING_TASKS: list[asyncio.Future[None]] = []


class RenderUpstreamProject(InfrastructureProject):
    name = "render.test.upstream"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [TARGET]

    def pulumi_program(self) -> None:
        pulumi.export("zone_name", "upstream.example.com")
        pulumi.export("environment", self.dctx.target.environment)


class RenderDownstreamProject(InfrastructureProject):
    name = "render.test.downstream"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return [RenderUpstreamProject.stack(target)]

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [TARGET]

    def pulumi_program(self) -> None:
        outputs = self.dctx.outputs(RenderUpstreamProject.stack(self.dctx.target))
        provider = self.dctx.provider_factory.aws_provider("aws")
        aws.s3.Bucket(
            "bucket",
            bucket=outputs["zone_name"].value,
            opts=ResourceOptions(provider=provider),
        )


class RenderUndeclaredProject(InfrastructureProject):
    name = "render.test.undeclared"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [TARGET]

    def pulumi_program(self) -> None:
        self.dctx.outputs(RenderUpstreamProject.stack(self.dctx.target))


class RenderFailingProject(InfrastructureProject):
    name = "render.test.failing"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [TARGET]

    def pulumi_program(self) -> None:
        raise ValueError("program failed")


class RenderFailingApplyProject(InfrastructureProject):
    name = "render.test.failing_apply"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [TARGET]

    def pulumi_program(self) -> None:
        def fail(_: str) -> str:
            raise ValueError("apply failed")

        pulumi.Output.from_input("value").apply(fail)


class RenderFailingWithPendingTaskProject(InfrastructureProject):
    name = "render.test.failing_pending"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [TARGET]

    def pulumi_program(self) -> None:
        PENDING_TASKS.append(asyncio.ensure_future(asyncio.sleep(0.01)))
        raise ValueError("program failed")


class RenderComputedProject(InfrastructureProject):
    """
    Project that reads back values a real provider would compute.
    """

    name = "render.test.computed"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [TARGET]

    def pulumi_program(self) -> None:
        aws_opts = ResourceOptions(
            provider=self.dctx.provider_factory.aws_provider("aws")
        )
        k8s_opts = ResourceOptions(
            provider=self.dctx.provider_factory.kubernetes_provider()
        )
        random_opts = ResourceOptions(
            provider=self.dctx.provider_factory.random_provider()
        )

        secret = k8s.core.v1.Secret(
            "secret",
            metadata=k8s.meta.v1.ObjectMetaArgs(name="secret"),
            string_data={"username": "admin"},
            opts=k8s_opts,
        )
        pulumi.export("secret_data", secret.data)

        password = random.RandomPassword("password", length=8, opts=random_opts)
        pulumi.export("password", password.result)

        zone = aws.route53.Zone("zone", name="example.com", opts=aws_opts)
        zone_data = aws.route53.get_zone_output(
            zone_id=zone.zone_id, opts=pulumi.InvokeOptions(provider=aws_opts.provider)
        )
        pulumi.export("zone_name", zone_data.name)
        pulumi.export("name_servers", zone_data.name_servers)

        certificate = aws.acm.Certificate(
            "certificate",
            domain_name="example.com",
            subject_alternative_names=["www.example.com"],
            opts=aws_opts,
        )
        pulumi.export(
            "validation",
            certificate.domain_validation_options.apply(
                lambda options: [o.resource_record_name for o in options]
            ),
        )
        pulumi.export("arn", certificate.arn)

        document = aws.iam.get_policy_document(
            statements=[
                aws.iam.GetPolicyDocumentStatementArgs(
                    actions=["s3:GetObject"], resources=["*"]
                )
            ],
            opts=pulumi.InvokeOptions(provider=aws_opts.provider),
        )
        pulumi.export("policy", document.json)


class RenderImportProject(InfrastructureProject):
    name = "render.test.import"

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [TARGET]

    def pulumi_program(self) -> None:
        provider = self.dctx.provider_factory.aws_provider("aws")
        aws.s3.Bucket(
            "bucket",
            opts=ResourceOptions(provider=provider, import_="existing"),
        )


def test_records_resources_with_provider_and_urn() -> None:
    upstream = RenderUpstreamProject.stack(TARGET)
    rendering = render(
        RenderDownstreamProject,
        TARGET,
        outputs={upstream: {"zone_name": "from.example.com"}},
    )

    bucket = rendering.one("aws:s3/bucket:Bucket", "bucket")
    assert bucket.inputs["bucket"] == "from.example.com"
    assert bucket.custom
    assert bucket.provider is not None and "pulumi:providers:aws" in bucket.provider
    assert bucket.urn.startswith("urn:pulumi:test::render.test.downstream::")
    assert bucket.urn.endswith("aws:s3/bucket:Bucket::bucket")
    assert bucket.import_id is None


def test_one_requires_exactly_one_match() -> None:
    rendering = render(RenderUpstreamProject, TARGET)

    with pytest.raises(LookupError):
        rendering.one("aws:s3/bucket:Bucket", "missing")


def test_captures_outputs_as_plain_values() -> None:
    rendering = render(RenderUpstreamProject, TARGET)

    assert rendering.outputs == {
        "zone_name": "upstream.example.com",
        "environment": "test",
    }


def test_render_with_dependencies_feeds_real_outputs() -> None:
    rendering = render_with_dependencies(RenderDownstreamProject, TARGET)

    bucket = rendering.one("aws:s3/bucket:Bucket", "bucket")
    assert bucket.inputs["bucket"] == "upstream.example.com"


def test_render_with_dependencies_uses_cache() -> None:
    cache: dict[InfrastructureStack, Rendering] = {}
    first = render_with_dependencies(RenderDownstreamProject, TARGET, cache=cache)
    second = render_with_dependencies(RenderDownstreamProject, TARGET, cache=cache)

    assert first is second
    assert RenderUpstreamProject.stack(TARGET) in cache


def test_missing_declared_outputs_fail_like_an_undeployed_stack() -> None:
    with pytest.raises(KeyError):
        render(RenderDownstreamProject, TARGET)


def test_undeclared_dependency_raises() -> None:
    with pytest.raises(UndeclaredDependencyError):
        render(RenderUndeclaredProject, TARGET)


@pytest.mark.parametrize(
    "project", [RenderFailingProject, RenderFailingApplyProject], ids=lambda p: p.name
)
def test_program_failure_raises_and_later_renders_work(
    project: type[InfrastructureProject],
) -> None:
    with pytest.raises(ValueError):
        render(project, TARGET)

    assert render(RenderUpstreamProject, TARGET).outputs["zone_name"]


def test_program_failure_finishes_pending_tasks() -> None:
    with pytest.raises(ValueError):
        render(RenderFailingWithPendingTaskProject, TARGET)

    assert PENDING_TASKS[-1].done()


def test_renders_repeat_in_one_process() -> None:
    first = render(RenderComputedProject, TARGET)
    second = render(RenderComputedProject, TARGET)

    assert first.outputs == second.outputs
    assert sorted(r.urn for r in first.resources) == sorted(
        r.urn for r in second.resources
    )


def test_computed_values_are_available() -> None:
    outputs = render(RenderComputedProject, TARGET).outputs

    assert b64decode(outputs["secret_data"]["username"]) == b"admin"
    assert outputs["password"] == "mock-random-password"
    assert outputs["zone_name"] == "example.com"
    assert outputs["name_servers"]
    assert outputs["validation"] == [
        "_validation.example.com",
        "_validation.www.example.com",
    ]
    assert outputs["arn"].startswith("arn:mock:")
    assert json.loads(outputs["policy"])["statements"][0]["actions"] == ["s3:GetObject"]


def test_records_calls() -> None:
    rendering = render(RenderComputedProject, TARGET)

    assert "aws:route53/getZone:getZone" in [c.token for c in rendering.calls]


def test_secret_inputs_are_recorded_without_envelopes() -> None:
    secret = render(RenderComputedProject, TARGET).one(
        "kubernetes:core/v1:Secret", "secret"
    )

    assert secret.inputs["stringData"] == {"username": "admin"}


def test_records_imports() -> None:
    bucket = render(RenderImportProject, TARGET).one("aws:s3/bucket:Bucket", "bucket")

    assert bucket.import_id == "existing"


def test_mock_provider_factory_returns_given_kubernetes_client() -> None:
    client = FakeKubernetesClient()
    factory = MockProviderFactory(kubernetes_client=client)

    assert factory.kubernetes_client() is client


def _stable_rendering(*resources: RecordedResource) -> Rendering:
    return Rendering(
        RenderUpstreamProject.stack(TARGET),
        resources=list(resources),
        outputs={"out": 1},
    )


def _stable_resource(name: str) -> RecordedResource:
    root = "urn:pulumi:test::noop::pulumi:pulumi:Stack$"
    return RecordedResource(
        urn=f"{root}aws:s3/bucket:Bucket::{name}",
        type="aws:s3/bucket:Bucket",
        name=name,
        inputs={"value": "v"},
        provider=f"{root}pulumi:providers:aws::aws::aws-id",
        import_id=None,
        custom=True,
    )


def test_yaml_does_not_depend_on_registration_order() -> None:
    a, b = _stable_resource("a"), _stable_resource("b")

    assert render_yaml(_stable_rendering(a, b)) == render_yaml(_stable_rendering(b, a))


def test_yaml_normalizes_mock_artifacts() -> None:
    data = yaml.safe_load(render_yaml(_stable_rendering(_stable_resource("a"))))
    entry = data["resources"][0]

    assert entry["urn"] == "urn:pulumi:test::noop::aws:s3/bucket:Bucket::a"
    assert entry["provider"] == "urn:pulumi:test::noop::pulumi:providers:aws::aws"
    assert entry["inputs"] == {"value": "v"}
    assert "import" not in entry
    assert data["outputs"] == {"out": 1}


def test_yaml_shows_imports() -> None:
    r = RecordedResource("urn:x", "t", "n", {}, None, "existing", True)

    data = yaml.safe_load(render_yaml(_stable_rendering(r)))

    assert data["resources"][0]["import"] == "existing"


def test_fake_kubernetes_client_returns_real_models() -> None:
    core = FakeKubernetesClient(backing_volume="data0").CoreV1Api()

    node = core.list_node(label_selector="has.data0.volume=true").items[0]
    assert node.status.addresses[0].type == "InternalIP"
    assert node.metadata.annotations["anything"] == "fake-anything"

    volume = core.read_persistent_volume("fake-name")
    assert isinstance(volume, kubernetes.client.V1PersistentVolume)
    assert volume.metadata.annotations["backing-volume"] == "data0"
