"""
tests/projects/test_projects -- Rendered Project Tests
======================================================

These tests render every stack of every project and check the results. New projects
are covered without any change here.
"""

import pytest

from cli.test import stacks_to_test
from infralib import InfrastructureStack
from infralib.testing import Rendering, render_with_dependencies, run_checks

_RENDERINGS: dict[InfrastructureStack, Rendering] = {}

STACKS = stacks_to_test()


def test_stacks_are_discovered() -> None:
    assert len(STACKS) > 0


@pytest.mark.parametrize("stack", STACKS, ids=lambda s: s.full_name)
def test_passes_checks(stack: InfrastructureStack) -> None:
    rendering = render_with_dependencies(stack.project, stack.target, cache=_RENDERINGS)

    assert [str(f) for f in run_checks(rendering)] == []
