"""
infralib/testing -- Offline Project Rendering
=============================================

This package runs infrastructure projects against Pulumi's mock runtime [1],
using dummy configuration and fake providers. It needs no Pulumi CLI, provider
plugins, credentials, or state, and it cannot affect real infrastructure.

It is deliberately not re-exported from infralib, because nothing outside of
`pcli test` and the test suite should load the mock runtime.

[1]: https://www.pulumi.com/docs/iac/guides/testing/unit/
"""

from .checks import Finding, run_checks
from .config import dummy_infrastructure_configuration
from .kubernetes import FakeKubernetesClient
from .provider import MockProviderFactory
from .render import (
    RecordedCall,
    RecordedResource,
    Rendering,
    render,
    render_with_dependencies,
    render_yaml,
    rendering_data,
)

__all__ = [
    "FakeKubernetesClient",
    "Finding",
    "MockProviderFactory",
    "RecordedCall",
    "RecordedResource",
    "Rendering",
    "dummy_infrastructure_configuration",
    "render",
    "render_with_dependencies",
    "render_yaml",
    "rendering_data",
    "run_checks",
]
