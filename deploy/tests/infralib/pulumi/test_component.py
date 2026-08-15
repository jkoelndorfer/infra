"""
tests/infralib/pulumi/test_component -- Pulumi InfrastructureComponent Tests
============================================================================

This file contains code to test the Pulumi InfrastructureComponent base class.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from infralib import DeploymentContext, InfrastructureComponent
from infralib.error import InvalidRegisterOutputsCallError

from .conftest import NoopPulumiRuntimeMock


class NoopInfrastructureComponentArgs:
    """
    Arguments class for the TestInfrastructureComponent.

    Does nothing and provides no arguments.
    """


class NoopInfrastructureComponent(
    InfrastructureComponent[NoopInfrastructureComponentArgs]
):
    """
    Test infrastructure component that does not provision any resources.
    """

    def provision(self) -> None:
        self.provision_called = True
        self.output("test", "testvalue")
        self.output("secondtest", "anothervalue")


@pytest.fixture
def infrastructure_component(
    noop_pulumi_runtime_mock: NoopPulumiRuntimeMock,
    test_deployment_context: DeploymentContext,
) -> NoopInfrastructureComponent:
    """
    Returns an InfrastructureComponent suitable for testing.
    """
    c = NoopInfrastructureComponent(
        name="noop_infrastructure_component",
        args=NoopInfrastructureComponentArgs(),
        dctx=test_deployment_context,
        pulumi_ro=MagicMock(),
    )

    # After creating the component, allow the event loop to run until all
    # pending tasks are completed.
    loop = asyncio.get_event_loop()
    pending = asyncio.all_tasks(loop)
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

    return c


class TestInfrastructureComponent:
    """
    Contains tests for the InfrastructureComponent class.
    """

    def test_provision_called(
        self,
        infrastructure_component: NoopInfrastructureComponent,
    ) -> None:
        """
        Tests that provision() is called by the constructor.

        Pulumi's documentation examples show that all resources are created
        at construction time.

        https://www.pulumi.com/docs/iac/guides/building-extending/components/build-a-component/
        """
        assert getattr(infrastructure_component, "provision_called", False)

    def test_outputs_registered(
        self,
        infrastructure_component: NoopInfrastructureComponent,
    ) -> None:
        """
        Tests that outputs are registered after the component is created.
        """
        ic = infrastructure_component
        expected_outputs = {
            "test": "testvalue",
            "secondtest": "anothervalue",
        }

        assert isinstance(ic._pulumi_ro, MagicMock)
        ic._pulumi_ro.assert_called_once_with(ic, expected_outputs)

    def test_register_outputs_raises_error(
        self,
        infrastructure_component: NoopInfrastructureComponent,
    ) -> None:
        """
        Tests that calling register_outputs on an InfrastructureComponent raises
        an error.

        The InfrastructureComponent arranges for register_outputs to be called on its own.
        """
        with pytest.raises(InvalidRegisterOutputsCallError):
            infrastructure_component.register_outputs(
                {
                    "this_should_fail": True,
                }
            )
