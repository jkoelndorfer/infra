"""
tests/infralib/deployment/test_target -- Deployment Target Tests
================================================================

This file contains code to test deployment targets.
"""

from typing import Any, Callable

import pytest

from infralib import DeploymentTarget as T, Environment as E


class TestDeploymentTarget:
    """
    Contains tests for the DeploymentTarget class.
    """

    def test_with_environment(self) -> None:
        """
        Tests that with_environment() returns a new DeploymentTarget with the specified environment.
        """
        target = T(E.DEV, None)

        assert target.with_environment(E.TEST).environment == E.TEST
        assert target.environment == E.DEV

    def test_with_region(self) -> None:
        """
        Tests that with_region() returns a new DeploymentTarget with the specified region.
        """
        target = T(E.TEST, "us-west-2")

        assert target.with_region("europe-west-1").region == "europe-west-1"
        assert target.region == "us-west-2"

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: T(E.TEST, None),
            lambda: T(E.TEST, "us-west-1"),
            lambda: T(E.DEV, None),
        ],
    )
    def test_eq_equal(self, factory: Callable[[], T]) -> None:
        """
        Tests that __eq__() returns True for equivalent DeploymentTargets.
        """
        a = factory()
        b = factory()

        assert a == b

    @pytest.mark.parametrize(
        "a, b",
        [
            (T(E.TEST, None), T(E.TEST, "us-west-1")),
            (T(E.TEST, None), T(E.DEV, None)),
            (T(E.TEST, None), True),
            (T(E.TEST, None), 1),
        ],
    )
    def test_eq_not_equal(self, a: T, b: Any) -> None:
        """
        Tests that __eq__() returns False for non-equivalent objects.
        """
        assert a != b

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: T(E.TEST, None),
            lambda: T(E.TEST, "us-west-1"),
            lambda: T(E.TEST, "europe-west-2"),
            lambda: T(E.DEV, None),
            lambda: T(E.DEV, "us-west-1"),
        ],
    )
    def test_hash_equivalent_objects(self, factory: Callable[[], T]) -> None:
        """
        Tests that __hash__() returns the same value for equivalent (but distinct) DeploymentTarget objects.
        """
        a = factory()
        b = factory()

        assert hash(a) == hash(b)

    @pytest.mark.parametrize(
        "target, expected",
        [
            (T(E.TEST, None), "DeploymentTarget(environment=test, region=None)"),
            (
                T(E.TEST, "us-west-2"),
                "DeploymentTarget(environment=test, region=us-west-2)",
            ),
        ],
    )
    def test_repr(self, target: T, expected: str) -> None:
        """
        Tests that __repr__() returns the expected value.
        """
        assert repr(target) == expected
