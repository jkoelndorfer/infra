"""
provision_server.py
-------------------

This pyinfra deployment runs the provision phase for a server's role.
"""

from pyinfra import host

from roles import provision

provision(host.data.role)
