"""
projects
========

This module contains all defined infralib InfrastructureProjects.
"""

from os.path import dirname
import importlib
import pkgutil

from infralib.deployment.project import all_projects, get_project


def discover_all_projects() -> None:
    """
    Discovers all files defined in this module and imports them.

    This enables infralib's registration code to track all defined projects.
    """
    # See https://docs.python.org/3/library/pkgutil.html.
    for _, pyname, _ in pkgutil.walk_packages([dirname(__file__)], __name__ + "."):
        importlib.import_module(pyname)


discover_all_projects()

__all__ = [
    "all_projects",
    "get_project",
]
