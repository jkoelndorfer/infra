"""
tests/cli/test_globals -- CLI Globals Tests
===========================================

This file contains code to test initialization of CLI globals.
"""

from pathlib import Path
from typing import Generator

from click import ClickException
import pytest

from cli.error import UninitializedGlobalsError
from cli.globals import _Globals, Globals
from infralib import (
    InfrastructureConfiguration,
    LocalBackendProvider,
    PulumiOperator,
)


@pytest.fixture
def cli_globals_env(
    monkeypatch: pytest.MonkeyPatch,
    local_backend_dir: Path,
    test_infrastructure_yaml_configuration_path: Path,
) -> None:
    """
    This fixture sets the environment variables needed to initialize globals.
    """
    config_path = test_infrastructure_yaml_configuration_path
    monkeypatch.setenv("INFRALIB_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("INFRALIB_LOCAL_BACKEND_PATH", str(local_backend_dir))


@pytest.fixture
def cli_globals(cli_globals_env: None) -> Generator[_Globals]:
    """
    Returns the CLI's object containing globals.
    """
    yield Globals

    Globals.uninitialize_globals()


class TestCLIGlobals:
    """
    This class tests initialization of CLI globals.
    """

    def test_initialize_globals_from_env(self, cli_globals: _Globals) -> None:
        """
        Tests initializing globals from the environment when the environment is correctly configured.
        """
        cli_globals.initialize_globals_from_env()

        assert isinstance(cli_globals.config, InfrastructureConfiguration)
        assert isinstance(cli_globals.pulumi_operator, PulumiOperator)

    def test_initialize_globals_from_env_no_config_path(
        self, monkeypatch: pytest.MonkeyPatch, cli_globals: _Globals
    ) -> None:
        """
        Tests initializing globals from the environment when no INFRALIB_CONFIG_PATH is specified.
        """
        monkeypatch.delenv("INFRALIB_CONFIG_PATH")
        with pytest.raises(ClickException):
            cli_globals.initialize_globals_from_env()

    def test_initialize_globals_from_env_no_backend_dir(
        self, monkeypatch: pytest.MonkeyPatch, cli_globals: _Globals
    ) -> None:
        """
        Tests initializing globals from the environment when no INFRALIB_CONFIG_PATH is specified.
        """
        monkeypatch.delenv("INFRALIB_LOCAL_BACKEND_PATH")
        with pytest.raises(ClickException):
            cli_globals.initialize_globals_from_env()

    def test_double_initialize_retains_globals(
        self,
        cli_globals: _Globals,
        test_infrastructure_configuration: InfrastructureConfiguration,
        local_backend_provider: LocalBackendProvider,
    ) -> None:
        """
        Tests that global objects are retained when initializing globals a second time.
        """
        cli_globals.initialize_globals(
            local_backend_provider, test_infrastructure_configuration
        )
        config = cli_globals.config
        pulumi_operator = cli_globals.pulumi_operator
        cli_globals.initialize_globals(
            local_backend_provider, test_infrastructure_configuration
        )

        assert config is cli_globals.config
        assert pulumi_operator is cli_globals.pulumi_operator

    def test_double_initialize_from_env_retains_globals(
        self, cli_globals: _Globals
    ) -> None:
        """
        Tests that global objects are retained when initializing globals a second
        time from the environment.
        """
        cli_globals.initialize_globals_from_env()
        config = cli_globals.config
        pulumi_operator = cli_globals.pulumi_operator
        cli_globals.initialize_globals_from_env()

        assert config is cli_globals.config
        assert pulumi_operator is cli_globals.pulumi_operator

    def test_uninitialized_globals_raise_error(self, cli_globals: _Globals) -> None:
        """
        Tests that attempting to access global values raises an error when globals are uninitialized.
        """
        with pytest.raises(UninitializedGlobalsError):
            cli_globals.config

        with pytest.raises(UninitializedGlobalsError):
            cli_globals.pulumi_operator

        with pytest.raises(UninitializedGlobalsError):
            cli_globals.pulumi_output_handler
