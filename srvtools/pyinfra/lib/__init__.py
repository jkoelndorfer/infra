"""
lib
---

This module contains common pyinfra library code.
"""


def patch_jinja2_env():
    """
    Patches the Jinja2 environment used by pyinfra to enable lstrip_blocks and trim_blocks.
    """
    from pyinfra.api import util
    util.Environment = Jinja2Environment


def Jinja2Environment(*args, **kwargs):
    from jinja2 import Environment

    kwargs["lstrip_blocks"] = True
    kwargs["trim_blocks"] = True

    return Environment(*args, **kwargs)
