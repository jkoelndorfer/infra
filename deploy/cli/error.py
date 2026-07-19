"""
cli/error
===========

This module contains errors defined by the CLI.
"""


class CLIError(Exception):
    """
    Top-level error for all errors originating from the CLI.
    """


class UninitializedGlobalsError(CLIError):
    """
    Error raised when global objects are used prior to initialization.
    """

    def __init__(self) -> None:
        super().__init__("CLI globals have not been initialized")
