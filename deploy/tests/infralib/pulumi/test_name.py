"""
tests/infralib/pulumi/test_name -- Pulumi Name Tests
====================================================

This file contains code to test Pulumi name helper functions.
"""

import pytest

from infralib import to_logical_name


class TestToLogicalName:
    """
    Contains tests for the to_logical_name function.
    """

    @pytest.mark.parametrize(
        "initial, expected",
        [
            ("Hello, World!", "Hello__World_"),
            ("namespace:pod", "namespace_pod"),
        ],
    )
    def test_to_logical_name(self, initial: str, expected: str) -> None:
        """
        Tests that the to_logical_name function returns the expected value.
        """

        assert to_logical_name(initial) == expected
