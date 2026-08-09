"""
infralib -- infrastructure core library
=======================================

This module contains infrastructure component code.
"""

from .config import (
    EmailChannel,
    InfrastructureConfiguration,
    InfrastructureConfigurationYAMLParser,
    NotificationCategory,
    NotificationChannel,
)
from .deployment.context import DeploymentContext
from .deployment.project import (
    all_projects,
    get_project,
    InfrastructureProject,
    project_name,
)
from .deployment.stack import InfrastructureStack, stack_name
from .deployment.target import DeploymentTarget, Environment
from .pulumi.backend import BackendProvider, LocalBackendProvider
from .pulumi.export import export_resource, exportable_resource
from .pulumi.name import is_project_name, is_stack_name, to_logical_name
from .pulumi.operator import PulumiOperator
from .pulumi.provider import ProviderFactory, StandardProviderFactory
from .pulumi.types import pcast, StackOutputResolver

__all__ = [
    "all_projects",
    "BackendProvider",
    "DeploymentContext",
    "DeploymentTarget",
    "EmailChannel",
    "Environment",
    "exportable_resource",
    "export_resource",
    "get_project",
    "InfrastructureConfiguration",
    "InfrastructureConfigurationYAMLParser",
    "InfrastructureProject",
    "InfrastructureStack",
    "is_project_name",
    "is_stack_name",
    "LocalBackendProvider",
    "NotificationCategory",
    "NotificationChannel",
    "pcast",
    "project_name",
    "ProviderFactory",
    "PulumiOperator",
    "stack_name",
    "StackOutputResolver",
    "StandardProviderFactory",
    "to_logical_name",
]
