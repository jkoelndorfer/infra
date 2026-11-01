"""
provision/provision_server -- Provision a Server
================================================

This pyinfra deployment provisions a server according to its role in the inventory.
"""

from pyinfra.context import host

from config import load_configuration
from roles import provision_role

provision_role(host.data.role, load_configuration())
