"""
tests/infralib/test_dependency -- Infrastructure Dependency Tests
=================================================================

This file contains code to test infralib dependency resolution.
"""

from typing import Any, Self

import pytest

from infralib.dependency import resolve_dependencies
from infralib.error import CircularDependencyError


class TDepender:
    """
    Class used to test dependency resolution.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._dependencies: list[Self] = list()

    def dependencies(self) -> list[Self]:
        # Reverse sorting by name here allows us to define dependencies in
        # lexical order and verify dependency resolution in reverse-lexical
        # order.
        return sorted(self._dependencies, key=lambda x: x.name, reverse=True)

    def set_dependencies(self, *dependencies: Self) -> None:
        self._dependencies = list(dependencies)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return self.name == other.name

    def __repr__(self) -> str:
        return self.name


class TestResolveDependencies:
    """
    Contains tests for the resolve_dependencies function.
    """

    def test_simple_direct(self) -> None:
        """
        Test case for a simple, direct dependency chain.

        A → B → C → D → E
        """
        A, B, C, D, E = [TDepender(x) for x in ["A", "B", "C", "D", "E"]]

        A.set_dependencies(B)
        B.set_dependencies(C)
        C.set_dependencies(D)
        D.set_dependencies(E)

        resolved = resolve_dependencies(A)

        assert resolved == [E, D, C, B, A]

    def test_diamond(self) -> None:
        """
        Test case for a diamond dependency chain.

                     A
                    ↙︎ ↘︎
                   B   C
                    ↘︎ ↙︎
                     D
        """
        A, B, C, D = [TDepender(x) for x in ["A", "B", "C", "D"]]
        A.set_dependencies(B, C)
        B.set_dependencies(D)
        C.set_dependencies(D)

        resolved = resolve_dependencies(A)

        assert resolved == [D, C, B, A]

    def test_double_diamond(self) -> None:
        """
        Test case for a double-diamond dependency chain.

                     A
                    ↙︎ ↘︎
                   B   C
                    ↘︎ ↙︎
                     D
                    ↙︎ ↘︎
                   E   F
                    ↘︎ ↙︎
                     G
        """
        A, B, C, D, E, F, G = [
            TDepender(x) for x in ["A", "B", "C", "D", "E", "F", "G"]
        ]
        A.set_dependencies(B, C)
        B.set_dependencies(D)
        C.set_dependencies(D)
        D.set_dependencies(E, F)
        E.set_dependencies(G)
        F.set_dependencies(G)

        resolved = resolve_dependencies(A)

        assert resolved == [G, F, E, D, C, B, A]

    def test_multiple_root_diamond(self) -> None:
        r"""
        Test case for multiple roots in a diamond configuration.

                A             E
               ↙︎ ↘︎           ↙︎ ↘︎
              B   C         F   G
               ↘︎ ↙︎           ↘︎ ↙︎
                D             H
        """
        A, B, C, D, E, F, G, H = [
            TDepender(x) for x in ["A", "B", "C", "D", "E", "F", "G", "H"]
        ]

        A.set_dependencies(B, C)
        B.set_dependencies(D)
        C.set_dependencies(D)

        E.set_dependencies(F, G)
        F.set_dependencies(H)
        G.set_dependencies(H)

        resolved = resolve_dependencies(A, E)
        assert resolved == [D, C, B, A, H, G, F, E]

    def test_multiple_root_one_root_in_dependency_chain(self) -> None:
        """
        Test case for multiple roots, where one root is in the dependency chain of another root.

                A      ┌────► E
               ↙︎ ↘︎     │     ↙︎ ↘︎
              B   C    │    F   G
               ↘︎ ↙︎     │     ↘︎ ↙︎
                D ─────┘      H
        """
        A, B, C, D, E, F, G, H = [
            TDepender(x) for x in ["A", "B", "C", "D", "E", "F", "G", "H"]
        ]

        A.set_dependencies(B, C)
        B.set_dependencies(D)
        C.set_dependencies(D)
        D.set_dependencies(E)
        E.set_dependencies(F, G)
        F.set_dependencies(H)
        G.set_dependencies(H)

        resolved = resolve_dependencies(A, E)
        assert resolved == [H, G, F, E, D, C, B, A]

    def test_circular_dependency(self) -> None:
        """
        Test case for a circular dependency.

        A -> B -> C -> D -> A
        """
        A, B, C, D = [TDepender(x) for x in ["A", "B", "C", "D"]]
        A.set_dependencies(B)
        B.set_dependencies(C)
        C.set_dependencies(D)
        D.set_dependencies(A)

        with pytest.raises(CircularDependencyError) as excinfo:
            resolve_dependencies(A)

        assert excinfo.value.dependency_chain == [A, B, C, D, A]
