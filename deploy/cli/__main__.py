"""
cli -- deployment command-line interface to Pulumi
==================================================

This module is the primary interface to Pulumi in this repository. It provides
common scaffolding for Pulumi projects and their programs. Pulumi's Automation API
[1] is heavily used.

[1]: https://www.pulumi.com/docs/reference/pkg/python/pulumi/
"""

from os import environ

from .main import main


if __name__ == "__main__":
    # CLICK_PROG_NAME is set by the wrapper shell script so that
    # the "Usage" message shows the proper command to invoke.
    main(prog_name=environ.get("CLICK_PROG_NAME", None))
