"""
infralib/pulumi/types -- Pulumi Helper Types
============================================

This module contains helper type definitions for Pulumi code.
"""

from typing import Callable

from pulumi import automation as auto

from ..deployment.stack import InfrastructureStack


StackOutputResolver = Callable[[InfrastructureStack], auto.OutputMap]
