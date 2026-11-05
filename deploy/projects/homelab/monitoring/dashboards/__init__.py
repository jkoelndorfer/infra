"""
projects.homelab.monitoring.dashboards
======================================

This package defines the dashboards that Grafana provisions. Each dashboard is a
function that receives the DeploymentContext, so it can draw on the configuration,
and returns the dashboard's JSON model as a dictionary.

To add a dashboard, define its function in a module here and add it to DASHBOARDS.
"""

import json

from infralib import DeploymentContext

from .common import DATASOURCE_UID, Dashboard, DashboardFactory
from .traefik import traefik_dashboard

DASHBOARDS: dict[str, DashboardFactory] = {
    "traefik.json": traefik_dashboard,
}
"""
Each dashboard's function, keyed by the name of the file Grafana provisions it from.
"""


def dashboard_files(dctx: DeploymentContext) -> dict[str, str]:
    """
    Returns the JSON of each dashboard, keyed by file name.
    """
    return {
        name: json.dumps(factory(dctx), indent=2, sort_keys=True) + "\n"
        for name, factory in DASHBOARDS.items()
    }


__all__ = [
    "DASHBOARDS",
    "DATASOURCE_UID",
    "Dashboard",
    "DashboardFactory",
    "dashboard_files",
]
