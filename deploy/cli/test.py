"""
cli/test
========

This module contains commands that test infralib projects offline.

These commands render projects against Pulumi's mock runtime using dummy
configuration. They never load real configuration or touch a backend, so main()
does not initialize CLI globals for them.
"""

import json

import click
from infralib import Environment, InfrastructureStack, all_projects
from infralib.error import NoSuchProjectError
from infralib.testing import (
    Rendering,
    render_with_dependencies,
    render_yaml,
    rendering_data,
    run_checks,
)
from projects import get_project

from .main import main

_optional_project = click.option(
    "--project",
    "-p",
    help="The infrastructure project. Defaults to every project.",
    default=None,
)


def stacks_to_test(project: str | None = None) -> list[InfrastructureStack]:
    """
    Returns the stacks to test: those of one project, or those of every project under
    `projects`. Projects that are defined by the test suite are also registered, and
    they only count if they are named.
    """
    if project is not None:
        try:
            selected = [get_project(project)]
        except NoSuchProjectError as e:
            raise click.ClickException(str(e)) from e
    else:
        selected = sorted(
            (p for p in all_projects() if p.__module__.startswith("projects.")),
            key=lambda p: p.name,
        )

    return [p.stack(t) for p in selected for t in p.deployment_targets()]


def _render_all(
    stacks: list[InfrastructureStack],
) -> list[tuple[InfrastructureStack, Rendering | Exception]]:
    """
    Renders each stack, keeping going after a failure so that one broken dependency
    does not hide the state of everything else.
    """
    cache: dict[InfrastructureStack, Rendering] = {}
    results: list[tuple[InfrastructureStack, Rendering | Exception]] = []
    for stack in stacks:
        try:
            rendering = render_with_dependencies(
                stack.project, stack.target, cache=cache
            )
            results.append((stack, rendering))
        except Exception as e:
            results.append((stack, e))
    return results


@main.group("test")
def test() -> None:
    """
    Test projects offline, using mocks and dummy configuration.

    These commands cannot affect real infrastructure, and they need no credentials,
    state, or Pulumi CLI. Passing them does not show that a deployment will succeed.
    Provider validation, permissions, and collisions with existing resources need a
    preview.
    """


@test.command("render")
@_optional_project
@click.option(
    "--environment",
    "-e",
    type=click.Choice(Environment, case_sensitive=False),
    help="Only show stacks in this environment.",
)
@click.option("--region", "-r", help="Only show stacks in this cloud region.")
@click.option("--type", "type_", help="Only show resources with this type token.")
@click.option("--name", help="Only show resources with this logical name.")
@click.option("--json", "as_json", is_flag=True, help="Print JSON instead of YAML.")
def render_cmd(
    project: str | None,
    environment: Environment | None,
    region: str | None,
    type_: str | None,
    name: str | None,
    as_json: bool,
) -> None:
    """
    Print the resources that stacks would create, in a stable order.

    To see what a change does, compare this output between two revisions.
    """
    stacks = [
        s
        for s in stacks_to_test(project)
        if (environment is None or s.target.environment == environment)
        and (region is None or s.target.region == region)
    ]
    if not stacks:
        raise click.ClickException("no stacks match")

    json_data = {}
    failures = 0
    for stack, result in _render_all(stacks):
        if isinstance(result, Exception):
            failures += 1
            click.echo(f"{stack.full_name}: render failed: {result!r}", err=True)
            continue
        result.resources = [
            r
            for r in result.resources
            if (type_ is None or r.type == type_) and (name is None or r.name == name)
        ]
        if as_json:
            json_data[stack.full_name] = rendering_data(result)
        else:
            click.echo(f"--- # {stack.full_name}")
            click.echo(render_yaml(result), nl=False)

    if as_json:
        click.echo(json.dumps(json_data, indent=2, sort_keys=True))
    if failures:
        raise click.ClickException(f"{failures} stack(s) failed to render")


@test.command("check")
@_optional_project
def check_cmd(project: str | None) -> None:
    """
    Render stacks, and check them for mistakes that mocks do not catch by themselves.
    """
    results = _render_all(stacks_to_test(project))
    problems = 0
    for stack, result in results:
        if isinstance(result, Exception):
            problems += 1
            click.echo(f"{stack.full_name}: render failed: {result!r}")
            continue
        for finding in run_checks(result):
            problems += 1
            click.echo(f"{stack.full_name}: {finding}")

    if problems:
        raise click.ClickException(f"{problems} problem(s) in {len(results)} stack(s)")
    click.echo(f"{len(results)} stack(s) passed")
