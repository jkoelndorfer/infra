"""
infralib/pulumi/types -- Pulumi Helper Types
============================================

This module contains helper type definitions for Pulumi code.
"""

from typing import Callable, TypeVar

from pulumi import automation as auto, Output

from ..deployment.stack import InfrastructureStack


T = TypeVar("T")


def pcast(o: Output[T]) -> T:  # pragma: nocover
    """
    "Pulumi Cast".

    This function exists only to satisfy the type checker in some limited
    scenarios. Pulumi exposes many Output types, but some object parameters
    are **type-checked to accept only the plain type, not the Output.**
    However, at runtime these Output types are, in fact, accepted.

    To work around that, we can "cast" the object to its plain type. Note
    this isn't a real cast. The underlying object is still an Output.
    """
    return o  # type: ignore


StackOutputResolver = Callable[[InfrastructureStack], auto.OutputMap]
