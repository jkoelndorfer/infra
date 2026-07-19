"""
cli/globals
===========

This module contains global variables used by the infra deploy CLI.
"""

from os import environ
from pathlib import Path

import click

from infralib import (
    BackendProvider,
    InfrastructureConfiguration,
    InfrastructureConfigurationYAMLParser,
    LocalBackendProvider,
    StandardProviderFactory,
    PulumiOperator,
)
from .error import UninitializedGlobalsError
from .output import PulumiOutputHandler


class _Globals:
    """
    Class that holds globals used by the CLI.
    """

    def __init__(self) -> None:
        self._config: InfrastructureConfiguration | None = None
        self._pulumi_operator: PulumiOperator | None = None
        self._pulumi_output_handler: PulumiOutputHandler | None = None

    @property
    def config(self) -> InfrastructureConfiguration:
        """
        Returns the current configuration.
        """
        if self._config is None:
            raise UninitializedGlobalsError()

        return self._config

    @property
    def pulumi_operator(self) -> PulumiOperator:
        """
        Returns the current Pulumi operator.
        """
        if self._pulumi_operator is None:
            raise UninitializedGlobalsError()

        return self._pulumi_operator

    @property
    def pulumi_output_handler(self) -> PulumiOutputHandler:
        """
        Returns the current Pulumi output handler.
        """
        if self._pulumi_output_handler is None:
            raise UninitializedGlobalsError()

        return self._pulumi_output_handler

    def initialize_globals(
        self, backend_provider: BackendProvider, config: InfrastructureConfiguration
    ) -> None:
        """
        Initialize CLI globals using the given backend and config.

        If globals are already initialized, this method does nothing.
        """
        if self._config is not None:
            return

        self._config = config

        provider_factory = StandardProviderFactory(
            aws_preferred_region=self._config.aws_organization.preferred_region,
            aws_base_assume_role=self._config.aws_organization.infrastructure_manager_role,
            gcp_impersonate_service_account=self._config.gcp_organization.infrastructure_manager_service_account,
            gcp_quota_project=self._config.gcp_organization.quota_project,
        )

        self._pulumi_operator = PulumiOperator(
            self._config, backend_provider, provider_factory
        )
        self._pulumi_output_handler = PulumiOutputHandler()

    def initialize_globals_from_env(self) -> None:
        """
        Initializes globals from the environment.
        """
        if self._config is not None:
            return

        config_path = environ.get("INFRALIB_CONFIG_PATH", None)
        if config_path is None:
            raise click.ClickException(
                "INFRALIB_CONFIG_PATH must be set to infrastructure configuration path"
            )

        backend_path = environ.get("INFRALIB_LOCAL_BACKEND_PATH", None)
        if backend_path is None:
            raise click.ClickException(
                "INFRALIB_LOCAL_BACKEND_PATH must be set to Pulumi backend path"
            )

        config_parser = InfrastructureConfigurationYAMLParser()
        config = config_parser.parse(Path(config_path))
        backend_provider = LocalBackendProvider(Path(backend_path))

        self.initialize_globals(backend_provider, config)

    def uninitialize_globals(self) -> None:
        """
        Uninitializes globals so that they can be initialized again.

        This is used for test runs.
        """
        self._config = None
        self._pulumi_operator = None
        self._pulumi_output_handler = None


Globals = _Globals()
