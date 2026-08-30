"""
cli/stack
=========

This module contains code to operate on infralib stacks.
"""

import os
import sys
from typing import Any

import click
from click.decorators import FC
from pulumi import automation as auto
from pulumi.automation._stack import RenameResult
from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureStack,
)
from infralib.error import InvalidDeploymentTargetError, NoSuchProjectError
from projects import get_project

from . import options
from .globals import Globals as G
from .main import main


def stack_options(f: FC) -> FC:
    """
    Applies the required stack selection options to a Click command.
    """
    for deco in [options.region, options.environment, options.project, options.refresh]:
        f = deco(f)
    return f


def make_stack(
    project: str, environment: Environment, region: str | None
) -> InfrastructureStack:
    """
    Given a set of stack selection options, returns the corresponding
    InfrastructureStack.
    """
    try:
        infra_project = get_project(project)
    except NoSuchProjectError as e:
        raise click.ClickException(str(e)) from e

    target = DeploymentTarget(environment, region)

    try:
        return infra_project.stack(target)
    except InvalidDeploymentTargetError as e:
        raise click.ClickException(str(e)) from e


def _stack_kwargs() -> dict[str, Any]:
    """
    Returns a set of common stack keyword arguments.
    """
    return {
        "on_output": G.pulumi_output_handler.on_output,
        "on_error": G.pulumi_output_handler.on_error,
        "color": "always",
    }


@main.group("stack")
def stack() -> None:
    """
    Perform operations on stacks.
    """


@stack.command("up")
@stack_options
@options.confirm
def up(
    project: str,
    environment: Environment,
    region: str | None,
    refresh: bool,
    confirm: bool,
) -> auto.UpResult | None:
    """
    Performs a `pulumi up` on the specified stack.
    """
    stack = make_stack(project, environment, region)

    if confirm:
        G.pulumi_operator.stack.preview(stack, do_refresh=refresh, **_stack_kwargs())
        confirmed = click.confirm(f"\nproceed with upping stack {stack}?")
    else:
        confirmed = True

    if not confirmed:
        click.echo("stack up aborted")
        return None

    # Extra whitespace is not needed if there was no preview.
    if confirm:
        click.echo()

    # If we confirmed the destroy, the refresh already happened via the
    # preview_destroy above. No reason to refresh again.
    refresh = refresh and not confirm
    up_result = G.pulumi_operator.stack.up(stack, do_refresh=refresh, **_stack_kwargs())

    return up_result


@stack.command("destroy")
@stack_options
@options.confirm
def destroy(
    project: str,
    environment: Environment,
    region: str | None,
    refresh: bool,
    confirm: bool,
) -> auto.DestroyResult | None:
    """
    Performs a `pulumi destroy` on the specified stack.
    """
    stack = make_stack(project, environment, region)

    if confirm:
        G.pulumi_operator.stack.preview_destroy(
            stack, do_refresh=refresh, **_stack_kwargs()
        )
        confirmed = click.confirm(f"\nproceed with destroying stack {stack}?")
    else:
        confirmed = True

    if not confirmed:
        click.echo("stack destroy aborted")
        return None

    # Extra whitespace is not needed if there was no preview.
    if confirm:
        click.echo()

    # If we confirmed the destroy, the refresh already happened via the
    # preview_destroy above. No reason to refresh again.
    refresh = refresh and not confirm
    destroy_result = G.pulumi_operator.stack.destroy(
        stack, do_refresh=refresh, **_stack_kwargs()
    )
    return destroy_result


@stack.command("preview")
@stack_options
@click.option(
    "--destroy/--no-destroy", help="Preview a destroy operation.", default=False
)
def preview(
    project: str,
    environment: Environment,
    region: str | None,
    refresh: bool,
    destroy: bool,
) -> auto.PreviewResult | auto.DestroyResult | None:
    """
    Performs a `pulumi preview` on the specified stack. Pass `--destroy` to preview destroy.
    """
    stack = make_stack(project, environment, region)

    result: auto.PreviewResult | auto.DestroyResult
    if destroy:
        result = G.pulumi_operator.stack.preview_destroy(stack, **_stack_kwargs())
    else:
        result = G.pulumi_operator.stack.preview(
            stack, do_refresh=refresh, **_stack_kwargs()
        )

    return result


@stack.command("rename")
@options.project
@options.environment
@options.region
@click.option("--to-project", help="The project to move the stack to.", default=None)
@click.option(
    "--to-environment", help="The environment to move the stack to.", default=None
)
@click.option(
    "--to-region", help="The region to move the stack to.", default="NO_REGION"
)
def rename(
    project: str,
    environment: Environment,
    region: str | None,
    to_project: str | None,
    to_environment: Environment | None,
    to_region: str | None,
) -> RenameResult | None:
    """
    Move a stack to a new project, environment, and/or region.

    Values passed to --to-* options set the destination. Unspecified
    --to-* options are unchanged.
    """
    if to_project is None:
        to_project = project
    if to_environment is None:
        to_environment = environment
    if to_region == "NO_REGION":
        to_region = region

    same_project = to_project == project
    same_environment = to_environment == environment
    same_region = to_region == region

    source_proj = G.pulumi_operator.stack.tools.try_state_only_project(project)
    source_stack = source_proj.stack(DeploymentTarget(Environment(environment), region))

    if same_project and same_environment and same_region:
        click.echo(f"renaming stack {source_stack} failed: source is destination")
        sys.exit(1)

    dest_stack = make_stack(to_project, to_environment, to_region)

    result = G.pulumi_operator.stack.rename(
        source_stack,
        dest_stack,
    )

    summary = result.summary
    assert summary is not None

    if summary.result == "succeeded":
        click.echo(f"renamed {source_stack.full_name} to {dest_stack.full_name}")

    return result


@stack.command("shell")
@options.project
@options.environment
@options.region
def shell(
    project: str,
    environment: Environment,
    region: str | None,
) -> None:  # pragma: no cover
    """
    Synthesizes the Pulumi project directory, then runs a shell in that directory.
    """
    stack = make_stack(project, environment, region)
    shell = os.environ["SHELL"]

    G.pulumi_operator.stack.shell(stack, [shell])
