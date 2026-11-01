"""
infralib/testing/render -- Offline Project Rendering
====================================================

This module runs a project's Pulumi program against Pulumi's mock runtime and
records what the program asked Pulumi to do.
"""

import asyncio
from base64 import b64encode
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
from typing import Any

import pulumi
from pulumi import automation as auto
from pulumi.runtime.mocks import MockMonitor
from pulumi.runtime.rpc import _special_secret_sig, _special_sig_key
import yaml

from ..config import InfrastructureConfiguration
from ..deployment.context import DeploymentContext
from ..deployment.project import InfrastructureProject
from ..deployment.stack import InfrastructureStack
from ..deployment.target import DeploymentTarget
from ..error import UndeclaredDependencyError
from ..pulumi.provider import ProviderFactory, ProviderFactoryFactory
from .config import dummy_infrastructure_configuration
from .provider import MockProviderFactory

_POLICY_DOCUMENT_TOKEN = "aws:iam/getPolicyDocument:getPolicyDocument"
_GET_ZONE_TOKEN = "aws:route53/getZone:getZone"
_ZONE_ID_PREFIX = "MOCKZONE-"

# Pulumi's mock runtime includes the root stack in URNs, but the real engine does not.
_MOCK_ROOT_STACK_TYPE = "pulumi:pulumi:Stack$"

# Results of provider functions that return values computed by the cloud provider.
# Keys use the provider's naming, not the Python SDK's. Add an entry here if a
# project starts reading a computed value from a new function.
_CALL_RESULTS: dict[str, dict[str, Any]] = {
    "aws:iam/getPolicy:getPolicy": {"arn": "arn:aws:iam::aws:policy/mock"},
    "aws:identitystore/getUser:getUser": {"userId": "mock-user-id"},
    _GET_ZONE_TOKEN: {"nameServers": ["ns1.example.net", "ns2.example.net"]},
    "aws:ssoadmin/getInstances:getInstances": {
        "arns": ["arn:aws:sso:::instance/ssoins-mock"],
        "identityStoreIds": ["d-mock"],
    },
}


def _plain(value: Any) -> Any:
    """
    Returns the value as it would be stored in state, with Pulumi's secret envelopes
    removed. Everything in a rendering is dummy data, and resources like Kubernetes
    Secrets wrap their inputs.
    """
    if isinstance(value, Enum):
        return value.value
    # Pulumi's wire format represents every number as a float.
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        if value.get(_special_sig_key) == _special_secret_sig:
            return _plain(value.get("value"))
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _computed_state(args: pulumi.runtime.MockResourceArgs) -> dict[str, Any]:
    """
    Returns plausible values for attributes that a cloud provider would compute.

    Programs read these and derive other resources from them. Without a value, they
    would crash, or they would render the string "None" into a policy.
    """
    state: dict[str, Any] = {}
    if args.typ.startswith("aws:"):
        state["arn"] = f"arn:mock:{args.typ}:{args.name}"
    if args.typ.startswith("random:"):
        state["result"] = f"mock-random-{args.name}"
        state["bcryptHash"] = f"mock-bcrypt-{args.name}"
    if args.typ == "kubernetes:core/v1:Secret":
        state["data"] = {
            k: b64encode(str(v).encode("utf-8")).decode("ascii")
            for k, v in (_plain(args.inputs.get("stringData")) or {}).items()
        }
    if args.typ == "aws:route53/zone:Zone":
        state["zoneId"] = f"{_ZONE_ID_PREFIX}{args.inputs.get('name')}"
    if args.typ == "aws:route53/record:Record":
        state["fqdn"] = args.inputs.get("name")
    if args.typ == "aws:acm/certificate:Certificate":
        names = [
            args.inputs.get("domainName"),
            *(args.inputs.get("subjectAlternativeNames") or []),
        ]
        state["domainValidationOptions"] = [
            {
                "domainName": name,
                "resourceRecordName": f"_validation.{name}",
                "resourceRecordType": "CNAME",
                "resourceRecordValue": f"_validation.mock.{name}",
            }
            for name in names
        ]
    return state


@dataclass(frozen=True)
class RecordedResource:
    """
    A resource that a program registered.
    """

    urn: str
    type: str
    name: str
    inputs: dict[str, Any]
    provider: str | None
    import_id: str | None
    custom: bool


@dataclass(frozen=True)
class RecordedCall:
    """
    A provider function, such as aws.iam.get_policy_document, that a program invoked.
    """

    token: str
    args: dict[str, Any]


@dataclass
class Rendering:
    """
    The result of rendering one stack.
    """

    stack: InfrastructureStack
    resources: list[RecordedResource] = field(default_factory=list)
    calls: list[RecordedCall] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)

    def of_type(self, type_: str) -> list[RecordedResource]:
        """
        Returns all resources with the given type token.
        """
        return [r for r in self.resources if r.type == type_]

    def one(self, type_: str, name: str) -> RecordedResource:
        """
        Returns the only resource with the given type token and logical name.
        """
        matches = [r for r in self.of_type(type_) if r.name == name]
        if len(matches) != 1:
            raise LookupError(f"expected one {type_} {name}; got {len(matches)}")
        return matches[0]


class _RecordingMocks(pulumi.runtime.Mocks):
    """
    Mocks that record every resource and call.

    Each resource's outputs echo its inputs, which is what lets programs that
    derive values from other resources run to completion.
    """

    def __init__(self, rendering: Rendering) -> None:
        self._rendering = rendering
        self.current = threading.local()

    def new_resource(
        self, args: pulumi.runtime.MockResourceArgs
    ) -> tuple[str, dict[str, Any]]:
        self._rendering.resources.append(
            RecordedResource(
                urn=self.current.urn,
                type=args.typ,
                name=args.name,
                inputs=_plain(dict(args.inputs)),
                provider=args.provider or None,
                import_id=args.resource_id or None,
                custom=bool(args.custom),
            )
        )
        id_ = args.resource_id or f"{args.name}-id"
        return (id_, {**_computed_state(args), **args.inputs})

    def call(
        self, args: pulumi.runtime.MockCallArgs
    ) -> tuple[dict[str, Any], list[tuple[str, str]]]:
        self._rendering.calls.append(RecordedCall(args.token, _plain(dict(args.args))))
        result = {**args.args, **_CALL_RESULTS.get(args.token, {})}
        if args.token == _GET_ZONE_TOKEN:
            result["name"] = str(args.args.get("zoneId")).removeprefix(_ZONE_ID_PREFIX)
        if args.token == _POLICY_DOCUMENT_TOKEN:
            # The real function merges statements into a canonical document. This
            # keeps the arguments readable, not canonical.
            result["json"] = json.dumps(args.args, sort_keys=True, default=str)
        return (result, [])


class _RecordingMonitor(MockMonitor):
    """
    MockMonitor that tells the mocks each resource's URN. The mock arguments do not
    include it, and MockMonitor computes it from the resource's parent.
    """

    def __init__(self, mocks: _RecordingMocks) -> None:
        super().__init__(mocks)
        self._recording_mocks = mocks

    def RegisterResource(self, request: Any) -> Any:
        self._recording_mocks.current.urn = self.make_urn(
            request.parent, request.type, request.name
        )
        register: Any = super().RegisterResource
        return register(request)


def _mock_provider_factory(dctx: DeploymentContext) -> ProviderFactory:
    return MockProviderFactory()


def render(
    project: type[InfrastructureProject],
    target: DeploymentTarget,
    config: InfrastructureConfiguration | None = None,
    outputs: Mapping[InfrastructureStack, Mapping[str, Any]] | None = None,
    provider_factory: ProviderFactoryFactory | None = None,
) -> Rendering:
    """
    Renders the stack for the given project and target.

    `outputs` holds the plain outputs of the stack's dependencies. As in a real run,
    reading a stack that is not a declared dependency raises
    UndeclaredDependencyError. Reading a declared stack that has no entry returns no
    outputs, as reading a stack that was never deployed does.
    """
    stack = project.stack(target)
    rendering = Rendering(stack)
    permitted = project.dependencies(target)
    known_outputs = outputs if outputs is not None else {}

    def resolve_outputs(requested: InfrastructureStack) -> auto.OutputMap:
        if requested not in permitted:
            raise UndeclaredDependencyError(
                requesting_stack=stack, outputting_stack=requested
            )
        return {
            k: auto.OutputValue(v, False)
            for k, v in known_outputs.get(requested, {}).items()
        }

    # NOTE: As of Pulumi 3.265.0, the mock runtime does not create the event loop
    # that Python 3.14 no longer creates implicitly.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    mocks = _RecordingMocks(rendering)

    def program() -> pulumi.Output[None]:
        dctx = DeploymentContext(
            target,
            config if config is not None else dummy_infrastructure_configuration(),
            provider_factory
            if provider_factory is not None
            else _mock_provider_factory,
            resolve_outputs,
        )
        project(dctx).pulumi_program()
        root = pulumi.runtime.settings.get_root_resource()

        def capture(values: dict[str, Any]) -> None:
            rendering.outputs.update(_plain(values))

        return pulumi.Output.all(**getattr(root, "outputs", {})).apply(capture)

    try:
        pulumi.runtime.set_mocks(
            mocks,
            project=project.name,
            stack=stack.name,
            preview=False,
            monitor=_RecordingMonitor(mocks),
        )
        run_program: Any = pulumi.runtime.test
        run_program(program)()
    finally:
        # A failed program leaves tasks behind, and each would report that it was
        # destroyed while pending.
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        pulumi.runtime.settings.reset_options()
        asyncio.set_event_loop(None)
        loop.close()

    return rendering


def _urn(urn: str) -> str:
    return urn.replace(_MOCK_ROOT_STACK_TYPE, "")


def rendering_data(rendering: Rendering) -> dict[str, Any]:
    """
    Returns the rendering as plain data, in an order that does not depend on the
    order in which Pulumi happened to register resources. Comparing this between two
    revisions shows what a change does, including resources that a program stopped
    creating, and URN changes, which can replace resources.
    """
    resources = []
    for r in sorted(rendering.resources, key=lambda r: r.urn):
        entry: dict[str, Any] = {"urn": _urn(r.urn)}
        if r.provider is not None:
            # The provider reference is "<urn>::<id>", and the id is a mock value.
            entry["provider"] = _urn(r.provider).rsplit("::", 1)[0]
        if r.import_id is not None:
            entry["import"] = r.import_id
        entry["inputs"] = r.inputs
        resources.append(entry)
    return {"resources": resources, "outputs": rendering.outputs}


def render_yaml(rendering: Rendering) -> str:
    """
    Returns the rendering as stable YAML.
    """
    return yaml.safe_dump(rendering_data(rendering), sort_keys=True, width=88)


def render_with_dependencies(
    project: type[InfrastructureProject],
    target: DeploymentTarget,
    config: InfrastructureConfiguration | None = None,
    provider_factory: ProviderFactoryFactory | None = None,
    cache: dict[InfrastructureStack, Rendering] | None = None,
) -> Rendering:
    """
    Renders the given stack, first rendering its dependencies so that their real
    output names and shapes are what the stack reads.

    Pass the same `cache` to several calls to render each stack only once.
    """
    renderings = cache if cache is not None else {}

    def visit(stack: InfrastructureStack) -> Rendering:
        if stack not in renderings:
            dependencies = stack.project.dependencies(stack.target)
            outputs = {d: visit(d).outputs for d in dependencies}
            renderings[stack] = render(
                stack.project, stack.target, config, outputs, provider_factory
            )
        return renderings[stack]

    return visit(project.stack(target))
