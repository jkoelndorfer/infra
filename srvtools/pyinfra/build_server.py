"""
build_server.py
---------------

This pyinfra deployment runs the build phase for a server's role.
"""

from pyinfra import host

from lib import patch_jinja2_env
from roles import build

patch_jinja2_env()
build(host.data.role)
