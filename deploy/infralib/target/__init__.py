"""
infralib/target -- Infrastructure Deployment Targets
====================================================
"""

from .environment import Environment
from .target import DeploymentTarget

__all__ = [
    "Environment",
    "DeploymentTarget",
]
