"""
roles
-----

This module contains pyinfra roles.

Roles contain the bulk of the configuration for a class of server.

By convention, servers have exactly one role.
"""

from importlib import import_module


def _role_module(role_name: str) -> object:
    return import_module(f".{role_name}", "roles")


def build(role_name: str) -> None:
    m = _role_module(role_name)
    m.build()  # type: ignore


def provision(role_name: str) -> None:
    m = _role_module(role_name)
    m.provision()  # type: ignore
