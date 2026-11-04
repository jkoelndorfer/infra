"""
provision/outputs -- Pulumi Stack Outputs
=========================================

This module reads the outputs of deployed Pulumi stacks for pyinfra deployments.
It uses the same backend as `pcli`, so INFRALIB_LOCAL_BACKEND_PATH and
PULUMI_CONFIG_PASSPHRASE (or PULUMI_CONFIG_PASSPHRASE_FILE) must be set.
"""

from functools import cache
from os import environ
from pathlib import Path

from pulumi import automation as auto

from infralib import (
    DeploymentContext,
    InfrastructureStack,
    LocalBackendProvider,
    PulumiOperator,
    PulumiOperatorTools,
)
from infralib.error import InvalidConfigurationError
from infralib.pulumi.provider import ProviderFactory

from config import load_configuration


# NOTE: pyinfra runs a deployment once per host, so this keeps from asking Pulumi
# for the same outputs each time.
@cache
def stack_outputs(stack: InfrastructureStack) -> auto.OutputMap:
    """
    Returns the outputs of a deployed stack, with secrets in plain text.

    NOTE: Secrets returned here must not be printed. Pass them only to operations
    that keep them out of pyinfra's output.
    """
    return _pulumi_operator().stack.outputs(stack)


@cache
def _pulumi_operator() -> PulumiOperator:
    path = environ.get("INFRALIB_LOCAL_BACKEND_PATH")
    if path is None:
        raise InvalidConfigurationError("INFRALIB_LOCAL_BACKEND_PATH must be set")

    tools = PulumiOperatorTools(
        config=load_configuration(),
        backend_provider=LocalBackendProvider(Path(path)),
        provider_factory_factory=_no_providers,
    )
    return PulumiOperator.new(tools)


def _no_providers(dctx: DeploymentContext) -> ProviderFactory:
    # Reading outputs never runs a stack's program, so nothing needs a provider.
    raise NotImplementedError("provisioning does not run Pulumi programs")
