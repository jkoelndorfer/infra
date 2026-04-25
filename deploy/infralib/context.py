"""
infralib/context -- Infrastructure Context
==========================================

This file defines the standard infrastructure deployment context
that is made available to Pulumi and pyinfra executions.
"""


class InfrastructureContext:
    """
    Context that is provided to all Pulumi and pyinfra executions.
    """

    def __init__(self) -> None:
        self.config = None
        self.environment = None
        self.region = None
