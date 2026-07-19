"""
tests/cli/conftest -- CLI Common Test Fixtures
==============================================

This file contains common test fixtures for CLI tests.
"""

from typing import Generator

from click import Group
from click.testing import CliRunner
import pytest

from infralib import (
    InfrastructureConfiguration,
    LocalBackendProvider,
)

import cli
from cli.globals import Globals as G


@pytest.fixture(scope="session")
def cli_main() -> Group:
    """
    Imports the CLI module to initialize the Click application.
    """
    return cli.main.main


@pytest.fixture(autouse=True)
def cli_globals(
    test_infrastructure_configuration: InfrastructureConfiguration,
    local_backend_provider: LocalBackendProvider,
) -> Generator[None]:
    """
    Fixture that initializes CLI globals with appropriate test values.
    """
    G.initialize_globals(local_backend_provider, test_infrastructure_configuration)

    yield

    G.uninitialize_globals()


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    Click CLI runner, used for testing Click applications.

    See https://click.palletsprojects.com/en/stable/testing/.
    """
    return CliRunner()
