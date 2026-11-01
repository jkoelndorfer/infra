"""
tests/cli/test_test_cmd -- `pcli test` Command Tests
====================================================

This module contains tests for the commands that test projects offline.
"""

import json
from typing import Generator

from click import Group
from click.testing import CliRunner
from pulumi import ResourceOptions
import pulumi_kubernetes as k8s
import pytest
import yaml

from cli.globals import Globals as G
from infralib import (
    DeploymentTarget,
    Environment,
    InfrastructureProject,
    InfrastructureStack,
)

BROKEN_NAME = "cmd.test.broken_name"
FAILING = "cmd.test.failing"


class BrokenNameProject(InfrastructureProject):
    name = BROKEN_NAME

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(Environment.TEST, None)]

    def pulumi_program(self) -> None:
        provider = self.dctx.provider_factory.kubernetes_provider()
        k8s.helm.v3.Release(
            "argo_workflows",
            chart="oci://example/chart:1@sha256:abc",
            opts=ResourceOptions(provider=provider),
        )


class FailingProject(InfrastructureProject):
    name = FAILING

    @classmethod
    def dependencies(cls, target: DeploymentTarget) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[DeploymentTarget]:
        return [DeploymentTarget(Environment.TEST, None)]

    def pulumi_program(self) -> None:
        raise ValueError("program failed")


@pytest.fixture
def no_real_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """
    Removes everything that the stack commands need from the environment.
    """
    G.uninitialize_globals()
    monkeypatch.delenv("INFRALIB_CONFIG_PATH", raising=False)
    monkeypatch.delenv("INFRALIB_LOCAL_BACKEND_PATH", raising=False)
    monkeypatch.delenv("PULUMI_CONFIG_PASSPHRASE", raising=False)
    monkeypatch.delenv("PULUMI_CONFIG_PASSPHRASE_FILE", raising=False)
    monkeypatch.setenv("PATH", "")
    yield


@pytest.mark.usefixtures("no_real_environment")
class TestWithoutRealEnvironment:
    def test_check_needs_no_environment_and_leaves_globals_alone(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(cli_main, ["test", "check", "-p", "noop"])

        assert result.exit_code == 0, result.output
        assert G._config is None
        assert G._pulumi_operator is None

    def test_stack_commands_still_need_environment(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(cli_main, ["stack", "list"])

        assert result.exit_code != 0
        assert "INFRALIB_CONFIG_PATH" in result.output


class TestRender:
    def test_prints_one_stack_as_yaml(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(
            cli_main, ["test", "render", "-p", BROKEN_NAME, "-e", "test"]
        )

        assert result.exit_code == 0, result.output
        assert result.output.startswith(f"--- # {BROKEN_NAME}/test\n")
        assert "argo_workflows" in yaml.safe_load(result.output)["resources"][0]["urn"]

    def test_prints_every_stack_in_a_stable_order(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        first = cli_runner.invoke(cli_main, ["test", "render"])
        second = cli_runner.invoke(cli_main, ["test", "render"])

        assert first.exit_code == 0, first.output
        assert first.output == second.output
        assert "--- # noop/dev\n" in first.output
        assert "--- # homelab.blocky/prod\n" in first.output
        assert BROKEN_NAME not in first.output
        assert len(list(yaml.safe_load_all(first.output))) > 1

    def test_filters_stacks(self, cli_main: Group, cli_runner: CliRunner) -> None:
        by_environment = cli_runner.invoke(cli_main, ["test", "render", "-e", "dev"])
        by_project = cli_runner.invoke(cli_main, ["test", "render", "-p", "noop"])

        assert "--- # noop/dev\n" in by_environment.output
        assert "--- # noop/prod\n" not in by_environment.output
        assert "--- # noop/dev\n" in by_project.output
        assert "--- # noop/prod\n" in by_project.output
        assert "homelab" not in by_project.output

    def test_filters_resources_and_prints_json(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(
            cli_main,
            [
                "test",
                "render",
                "-p",
                BROKEN_NAME,
                "--type",
                "kubernetes:helm.sh/v3:Release",
                "--name",
                "argo_workflows",
                "--json",
            ],
        )

        assert result.exit_code == 0, result.output
        resources = json.loads(result.output)[f"{BROKEN_NAME}/test"]["resources"]
        assert len(resources) == 1
        assert resources[0]["urn"].endswith("::argo_workflows")

    def test_filter_can_exclude_every_resource(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(
            cli_main, ["test", "render", "-p", BROKEN_NAME, "--name", "nothing"]
        )

        assert result.exit_code == 0, result.output
        assert "resources: []" in result.output

    @pytest.mark.parametrize(
        "args",
        [
            ["-p", "no.such.project"],
            ["-p", BROKEN_NAME, "-e", "prod"],
            ["-p", "noop", "-r", "no-such-region"],
        ],
    )
    def test_rejects_stacks_that_do_not_exist(
        self, cli_main: Group, cli_runner: CliRunner, args: list[str]
    ) -> None:
        result = cli_runner.invoke(cli_main, ["test", "render", *args])

        assert result.exit_code == 1
        assert "Error:" in result.output

    def test_reports_render_failures(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(cli_main, ["test", "render", "-p", FAILING])

        assert result.exit_code == 1
        assert "program failed" in result.output


class TestCheck:
    def test_all_real_projects_pass(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(cli_main, ["test", "check"])

        assert result.exit_code == 0, result.output
        assert "stack(s) passed" in result.output

    def test_reports_findings(self, cli_main: Group, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(cli_main, ["test", "check", "-p", BROKEN_NAME])

        assert result.exit_code == 1
        assert "[kubernetes-name]" in result.output
        assert "argo_workflows" in result.output

    def test_reports_render_failures(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(cli_main, ["test", "check", "-p", FAILING])

        assert result.exit_code == 1
        assert "render failed" in result.output
        assert "program failed" in result.output

    def test_rejects_unknown_project(
        self, cli_main: Group, cli_runner: CliRunner
    ) -> None:
        result = cli_runner.invoke(cli_main, ["test", "check", "-p", "no.such.project"])

        assert result.exit_code == 1
