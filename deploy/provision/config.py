"""
provision/config -- Provisioning Configuration
==============================================

This module loads infrastructure configuration for pyinfra deployments.
"""

from functools import cache
from os import environ
from pathlib import Path

from infralib import InfrastructureConfiguration, InfrastructureConfigurationYAMLParser
from infralib.error import InvalidConfigurationError


# NOTE: pyinfra runs a deployment once per host, so this keeps from parsing the
# configuration each time.
@cache
def load_configuration() -> InfrastructureConfiguration:
    """
    Loads the configuration at INFRALIB_CONFIG_PATH.
    """
    path = environ.get("INFRALIB_CONFIG_PATH")
    if path is None:
        raise InvalidConfigurationError("INFRALIB_CONFIG_PATH must be set")

    return InfrastructureConfigurationYAMLParser().parse(Path(path))
