"""
projects.homelab.monitoring.dashboards.common
=============================================

This module contains definitions shared by Grafana dashboards.
"""

from collections.abc import Callable
from typing import Any

from infralib import DeploymentContext

Dashboard = dict[str, Any]
"""
A Grafana dashboard JSON model [1].

[1]: https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/view-dashboard-json-model/
"""

DashboardFactory = Callable[[DeploymentContext], Dashboard]

DATASOURCE_UID = "victoriametrics"
"""
The UID of the provisioned VictoriaMetrics data source.
"""

DATASOURCE = {"type": "prometheus", "uid": DATASOURCE_UID}
"""
A reference to the provisioned VictoriaMetrics data source, for panels and queries.
"""


def legend_var(label: str) -> str:
    """
    Returns a reference to a label's value, for a query's legend format [1].

    [1]: https://grafana.com/docs/grafana/latest/datasources/prometheus/query-editor/#legend
    """
    return f"{{{{{label}}}}}"


def legend_vars(*labels: str, sep: str = " ") -> str:
    """
    Returns a legend format that joins the values of the given labels with sep.
    """
    return sep.join(legend_var(label) for label in labels)
