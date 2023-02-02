"""
roles/miniserv/build
--------------------

This module contains provision logic for the miniserv role.
"""

from os import path

from lib import vars

from pyinfra.operations import files

files_dir = path.join(path.dirname(__file__), "files")

def provision():
    pass
