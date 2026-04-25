"""
infralib/context/environment -- Deployment Environment
======================================================

This file defines deployment environment types.
"""

from enum import StrEnum


class Environment(StrEnum):
    """
    An enumeration containing all deployable environments.
    """

    DEV = "dev"
    PROD = "prod"
