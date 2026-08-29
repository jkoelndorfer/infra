"""
infralib/pulumi/operator/operator -- Pulumi Top-Level Operator
==============================================================

This module contains the definition for the top-level Pulumi operator.

The top-level operator is composed of sub-operators that operate within
bounded domains.
"""

from typing import Self

from .stack import PulumiStackOperator
from .tools import PulumiOperatorTools


class PulumiOperator:
    """
    PulumiOperator is responsible for interfacing with the Pulumi automation API.
    It provides an interface to instantiate stacks configured with a proper backend,
    refreshing and upping stacks, and lookup of outputs in dependent stacks.

    See the Pulumi Python SDK.

    https://www.pulumi.com/docs/reference/pkg/python/pulumi/
    """

    def __init__(
        self,
        tools: PulumiOperatorTools,
        stack: PulumiStackOperator,
    ) -> None:
        self.tools = tools
        self.stack = stack

    @classmethod
    def new(cls, tools: PulumiOperatorTools) -> Self:
        """
        Creates a new PulumiOperator with the standard set of sub-operators.
        """
        return cls(
            tools=tools,
            stack=PulumiStackOperator(tools),
        )
