"""
provision_server.py
-------------------

This pyinfra deployment runs the provision phase for a server's role.
"""

from pyinfra import host

from lib import patch_jinja2_env
from roles import provision

patch_jinja2_env()
provision(host.data.role)
