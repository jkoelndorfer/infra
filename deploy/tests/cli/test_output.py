"""
tests/cli/test_output -- CLI Output Tests
=========================================

This file contains code to test CLI output.
"""

from textwrap import dedent
from unittest.mock import call, Mock
from typing import Literal

import pytest

from cli.output import PulumiOutputHandler

# Pulumi emits this warning when a GCP provider is initialized and has
# no default project passed.
#
# See the PulumiOutputHandler for more information.
pulumi_gcp_no_project_warning = dedent("""
    warning: unable to detect a global setting for GCP Project.
    Pulumi will rely on per-resource settings for this operation.
    Set the GCP Project by using:
        `pulumi config set gcp:project <project>`
    If you would like to disable this warning use:
        `pulumi config set gcp:disableGlobalProjectWarning true`
""").strip()


@pytest.fixture
def pulumi_output_handler() -> PulumiOutputHandler:
    """
    Returns a PulumiOutputHandler that is suitable for use in testing.
    """
    output_handler = Mock(["__call__"])
    error_handler = Mock(["__call__"])

    poh = PulumiOutputHandler()
    poh.output_handler = output_handler
    poh.error_handler = error_handler

    return poh


class TestPulumiOutputHandler:
    """
    Contains tests for the PulumiOutputHandler class.
    """

    @pytest.mark.parametrize("stream", ["output", "error"])
    def test_filtering_gcp_project_warning(
        self,
        pulumi_output_handler: PulumiOutputHandler,
        stream: Literal["output", "error"],
    ) -> None:
        """
        Tests that the GCP project warning is filtered by Pulumi's output handler.
        """
        match stream:
            case "output":
                handler = pulumi_output_handler.output_handler
                on_fn = pulumi_output_handler.on_output
            case "error":
                handler = pulumi_output_handler.error_handler
                on_fn = pulumi_output_handler.on_error

        before_output = "unfiltered before output"
        after_output = "unfiltered after output"
        gcp_warn_lines = pulumi_gcp_no_project_warning.splitlines()

        on_fn(before_output)
        for ln in gcp_warn_lines:
            on_fn(ln)
        on_fn(after_output)

        assert isinstance(handler, Mock)
        handler.assert_has_calls(
            [
                call(before_output),
                call(after_output),
            ]
        )
        assert handler.call_count == 2
