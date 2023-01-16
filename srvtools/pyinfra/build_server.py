"""
build_server.py
---------------

This pyinfra deployment runs the build phase for a server's role.
"""

from pyinfra import host

from roles import build

build(host.data.role)
