"""
infralib/dependency -- Dependency Resolution
============================================

This module contains code to resolve perform basic dependency resolution.
"""

from typing import Iterator, Protocol, Sequence, Self, TypeVar

from .error import CircularDependencyError


class Depender(Protocol):
    """
    The Depender protocol describes objects that have a dependencies() method.
    """

    def dependencies(self) -> list[Self]:
        """
        Return a list of this object's direct dependencies.
        """
        raise NotImplementedError("protocol does not provide a concrete implementation")


T = TypeVar("T", bound=Depender)


def resolve_dependencies(*roots: T) -> Sequence[T]:
    """
    Given a list of root objects, resolves dependencies recursively
    and returns the list of dependencies in order.
    """
    ordered_deps: list[T] = list()

    # Dictionaries preserve insertion order, so we use that here instead
    # of a set.
    visiting: dict[T, bool] = dict()
    visited: set[T] = set()

    # The stack consists of a tuple of node and an iterator over the
    # node's dependencies. Using an iterator over the dependencies saves
    # us from iterating over the same dependency multiple times.
    stack: list[tuple[T, Iterator[T]]]

    current: T
    current_deps: Iterator[T]

    for root in roots:
        # When multiple root nodes are specified, one root may be a dependent
        # of another root. If that happens and we've already visited, we can
        # skip the already-visited root.
        if root in visited:
            continue

        stack = [(root, iter(root.dependencies()))]

        while len(stack) > 0:
            current, current_deps = stack[-1]

            # Get the next dependency of the current node.
            dep = next(current_deps, None)
            visiting[current] = True

            # If there isn't another dependency, we're done here. Remove this node
            # from the stack and visiting set and add it to he list of ordered
            # dependencies.
            if dep is None:
                stack.pop()
                del visiting[current]
                visited.add(current)
                ordered_deps.append(current)
                continue

            # If the dependency is currently being visited, we have a cicular dependency.
            if dep in visiting:
                raise CircularDependencyError([*visiting, dep])

            # If we've already visited the node, skip processing it.
            if dep in visited:
                continue

            stack.append((dep, iter(dep.dependencies())))

    return ordered_deps
