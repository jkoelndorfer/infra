"""
cli/stack
=========

This module contains code to operate on infralib stacks.
"""

from typing import Any

import click
from click.decorators import FC
from pulumi import automation as auto
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
        G.pulumi_operator.preview(stack, do_refresh=refresh, **_stack_kwargs())
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
    up_result = G.pulumi_operator.up(stack, do_refresh=refresh, **_stack_kwargs())

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
        G.pulumi_operator.preview_destroy(stack, do_refresh=refresh, **_stack_kwargs())
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
    destroy_result = G.pulumi_operator.destroy(
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
        result = G.pulumi_operator.preview_destroy(stack, **_stack_kwargs())
    else:
        result = G.pulumi_operator.preview(stack, do_refresh=refresh, **_stack_kwargs())

    return result
