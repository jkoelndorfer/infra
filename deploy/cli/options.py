"""
cli/options
===========

This module contains common command-line option definitions for the CLI.
"""

from click import Choice, option

from infralib import Environment

environment = option(
    "--environment",
    "-e",
    type=Choice(Environment, case_sensitive=False),
    help="The environment to deploy to.",
    required=True,
)
confirm = option(
    "--confirm/--no-confirm", help="Prompt for confirmation.", default=True
)
project = option(
    "--project", "-p", help="The infrastructure project to operate on.", required=True
)
refresh = option(
    "--refresh/--no-refresh",
    help="Refresh before performing any stack operations.",
    default=True,
)
region = option("--region", "-r", help="The cloud region to deploy to.", default=None)
