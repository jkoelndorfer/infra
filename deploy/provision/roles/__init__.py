"""
provision/roles -- Server Roles
===============================

Roles contain the configuration for a class of server. By convention, servers have
exactly one role.
"""

from collections.abc import Callable

from infralib import InfrastructureConfiguration
from infralib.error import InvalidConfigurationError

from .edgerouter import provision as provision_edgerouter
from .kserv import provision as provision_kserv

_ROLES: dict[str, Callable[[InfrastructureConfiguration], None]] = {
    "edgerouter": provision_edgerouter,
    "kserv": provision_kserv,
}


def provision_role(role: str, config: InfrastructureConfiguration) -> None:
    """
    Runs the provisioning logic for a role.
    """
    if role not in _ROLES:
        raise InvalidConfigurationError(f"unknown role: {role!r}")

    _ROLES[role](config)
