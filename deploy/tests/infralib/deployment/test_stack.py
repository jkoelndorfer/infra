"""
tests/infralib/deployment/test_stack -- Infrastructure Stack Tests
==================================================================

This file contains code to test infrastructure stacks.
"""

from typing import Any

import pytest

from infralib import (
    DeploymentTarget as T,
    Environment as E,
    InfrastructureStack,
    InfrastructureProject,
)
from infralib.error import InvalidInfrastructureNameError


class CharlieProject(InfrastructureProject):
    """
    First-tier infrastructure project used for stack testing.
    """

    name = "charlie"

    @classmethod
    def dependencies(cls, target: T) -> list[InfrastructureStack]:
        return []

    @classmethod
    def deployment_targets(cls) -> list[T]:
        return [
            T(E.TEST, None),
            T(E.TEST, "europe-west-1"),
            T(E.TEST, "us-west-2"),
        ]

    def pulumi_program(self) -> None:
        pass


class DeltaProject(InfrastructureProject):
    """
    Second-tier infrastructure project used for stack testing.
    """

    name = "delta"

    @classmethod
    def dependencies(cls, target: T) -> list[InfrastructureStack]:
        return [CharlieProject.stack(target)]

    @classmethod
    def deployment_targets(cls) -> list[T]:
        return [
            T(E.TEST, None),
            T(E.TEST, "europe-west-1"),
            T(E.TEST, "us-west-2"),
            T(E.DEV, "europe-west-1"),
        ]

    def pulumi_program(self) -> None:
        pass


class TestInfrastructureStack:
    """
    Contains tests for the InfrastructureStack class.
    """

    @pytest.mark.parametrize(
        "stack, expected_name",
        [
            (CharlieProject.stack(T(E.TEST, None)), "test"),
            (CharlieProject.stack(T(E.TEST, "us-west-2")), "test.us-west-2"),
        ],
    )
    def test_name(self, stack: InfrastructureStack, expected_name: str) -> None:
        """
        Tests that the name property returns the expected name.
        """
        assert stack.name == expected_name

    @pytest.mark.parametrize(
        "stack, expected_name",
        [
            (CharlieProject.stack(T(E.TEST, None)), "charlie/test"),
            (CharlieProject.stack(T(E.TEST, "us-west-2")), "charlie/test.us-west-2"),
        ],
    )
    def test_full_name(self, stack: InfrastructureStack, expected_name: str) -> None:
        """
        Tests that the full_name property returns the expected name.
        """
        assert stack.full_name == expected_name

    def test_invalid_stack_name(self) -> None:
        """
        Tests that name raises an InvalidInfrastructureNameError when the name is invalid.
        """
        stack = InfrastructureStack(CharlieProject, T(E.TEST, "invalid/region"))

        with pytest.raises(InvalidInfrastructureNameError):
            stack.name

    @pytest.mark.parametrize(
        "target", [T(E.TEST, None), T(E.TEST, "europe-west-1"), T(E.TEST, "us-west-2")]
    )
    def test_dependencies(self, target: T) -> None:
        """
        Tests that dependencies() returns the expected set of dependencies.
        """
        deps = DeltaProject.stack(target).dependencies()

        assert CharlieProject.stack(target) in deps

    @pytest.mark.parametrize(
        "a, b",
        [
            (
                CharlieProject.stack(T(E.TEST, None)),
                InfrastructureStack(CharlieProject, T(E.TEST, None)),
            ),
        ],
    )
    def test_eq_when_equal(
        self, a: InfrastructureStack, b: InfrastructureStack
    ) -> None:
        """
        Tests that __eq__() returns True for equivalent stacks.
        """
        assert a == b

    @pytest.mark.parametrize(
        "a, b",
        [
            (
                CharlieProject.stack(T(E.TEST, None)),
                DeltaProject.stack(T(E.TEST, None)),
            ),
            (
                CharlieProject.stack(T(E.TEST, None)),
                CharlieProject.stack(T(E.TEST, "us-west-2")),
            ),
        ],
    )
    def test_eq_when_not_equal(
        self, a: InfrastructureStack, b: InfrastructureStack
    ) -> None:
        """
        Tests that __eq__() returns False for non-equivalent stacks.
        """
        assert a != b

    @pytest.mark.parametrize(
        "other",
        [
            True,
            1,
            0,
            "InfrastructureStack",
            None,
        ],
    )
    def test_eq_uncomparable_type(self, other: Any) -> None:
        """
        Tests that __eq__() returns False when a stack is compared to a an uncomparable type.
        """
        assert CharlieProject.stack(T(E.TEST, None)) != other

    @pytest.mark.parametrize(
        "a, b",
        [
            (
                CharlieProject.stack(T(E.TEST, None)),
                InfrastructureStack(CharlieProject, T(E.TEST, None)),
            ),
            (
                DeltaProject.stack(T(E.TEST, None)),
                InfrastructureStack(DeltaProject, T(E.TEST, None)),
            ),
        ],
    )
    def test_hash_equivalent_stacks(
        self, a: InfrastructureStack, b: InfrastructureStack
    ) -> None:
        """
        Tests that __hash__() returns the same value for two equivalent stacks.
        """
        assert hash(a) == hash(b)

    @pytest.mark.parametrize(
        "stack, expected",
        [
            (CharlieProject.stack(T(E.TEST, None)), "charlie/test"),
            (CharlieProject.stack(T(E.TEST, "us-west-2")), "charlie/test.us-west-2"),
            (DeltaProject.stack(T(E.DEV, "europe-west-1")), "delta/dev.europe-west-1"),
        ],
    )
    def test_str(self, stack: InfrastructureStack, expected: str) -> None:
        """
        Tests that __str__() returns the stack's full name, as expected by Pulumi.
        """
        assert str(stack) == expected

    @pytest.mark.parametrize(
        "stack, expected",
        [
            (
                CharlieProject.stack(T(E.TEST, None)),
                "InfrastructureStack(charlie/test)",
            ),
            (
                DeltaProject.stack(T(E.DEV, "europe-west-1")),
                "InfrastructureStack(delta/dev.europe-west-1)",
            ),
        ],
    )
    def test_repr(self, stack: InfrastructureStack, expected: str) -> None:
        """
        Tests that __repr__() returns the expected representation of a stack.
        """
        assert repr(stack) == expected
