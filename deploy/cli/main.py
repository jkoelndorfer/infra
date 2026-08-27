"""
cli/main
========

This module contains the Click entrypoint group.
"""

import click
from IPython import start_ipython

from projects import all_projects, get_project

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


@main.command("python-shell")
def python_shell() -> None:  # pragma: no cover
    """
    Launches a Python shell that can be used for debugging.
    """
    click.echo("Launching IPython shell with configured variables\n")
    user_ns_vars = {
        "all_projects": (all_projects, "function to get all projects"),
        "config": (G.config, "global infrastructure configuration"),
        "get_project": (get_project, "function to get named project"),
        "pulumi_operator": (G.pulumi_operator, "Pulumi operator"),
    }
    var_name_width = max(len(k) for k in user_ns_vars) + 2

    for var in user_ns_vars:
        help_text = user_ns_vars[var][1]
        var_just = f"{var}:".ljust(var_name_width)
        click.echo(f"{var_just} {help_text}")

    start_ipython(
        argv=["--no-banner"],
        user_ns={k: v[0] for k, v in user_ns_vars.items()},
    )
