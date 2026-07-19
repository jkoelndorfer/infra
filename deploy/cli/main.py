"""
cli/main
========

This module contains the Click entrypoint group.
"""

import click

from .globals import Globals as G


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """
    Infrastructure deployment CLI.
    """
    G.initialize_globals_from_env()

    @ctx.call_on_close
    def cleanup() -> None:
        G.pulumi_operator.cleanup()
