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


def row(title: str, y: int) -> dict[str, Any]:
    """
    Returns a row that heads the panels below it, at height y.
    """
    return {
        "type": "row",
        "title": title,
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "panels": [],
    }


def target(
    expr: str, legend: str, ref_id: str = "A", instant: bool = False
) -> dict[str, Any]:
    """
    Returns a query of the VictoriaMetrics data source. An instant query returns one
    value per series, as a table.
    """
    return {
        "datasource": dict(DATASOURCE),
        "expr": expr,
        "legendFormat": legend,
        "refId": ref_id,
        "range": not instant,
        "instant": instant,
        "format": "table" if instant else "time_series",
    }


def stat(
    title: str,
    description: str,
    expr: str,
    unit: str,
    x: int,
    y: int,
    thresholds: list[dict[str, Any]] | None = None,
    decimals: int | None = None,
    legend: str | None = None,
) -> dict[str, Any]:
    """
    Returns a 6x4 panel that shows the latest value of each series, over a graph of
    its history. Series are named by legend, or by the title if there is none.
    """
    defaults: dict[str, Any] = {
        "unit": unit,
        "color": {"mode": "thresholds"},
        "thresholds": {
            "mode": "absolute",
            "steps": thresholds or [{"color": "text", "value": None}],
        },
    }
    if decimals is not None:
        defaults["decimals"] = decimals
    return {
        "type": "stat",
        "title": title,
        "description": description,
        "datasource": dict(DATASOURCE),
        "gridPos": {"h": 4, "w": 6, "x": x, "y": y},
        "targets": [target(expr, legend=title if legend is None else legend)],
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": "value",
            "graphMode": "area",
            "textMode": "auto",
            "justifyMode": "auto",
            "orientation": "auto",
        },
    }


def timeseries(
    title: str,
    description: str,
    targets: list[dict[str, Any]],
    grid_pos: dict[str, int],
    unit: str,
    overrides: list[dict[str, Any]] | None = None,
    stacked: bool = True,
    fill_opacity: int = 25,
) -> dict[str, Any]:
    """
    Returns a graph of the series that targets return, from zero, with a legend of
    each one's mean and maximum.
    """
    return {
        "type": "timeseries",
        "title": title,
        "description": description,
        "datasource": dict(DATASOURCE),
        "gridPos": grid_pos,
        "targets": targets,
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "min": 0,
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": "line",
                    "lineWidth": 1,
                    "fillOpacity": fill_opacity,
                    "stacking": {
                        "mode": "normal" if stacked else "none",
                        "group": "A",
                    },
                    "showPoints": "never",
                    "spanNulls": False,
                },
            },
            "overrides": overrides or [],
        },
        "options": {
            "legend": {
                "displayMode": "table",
                "placement": "right",
                "showLegend": True,
                "calcs": ["mean", "max"],
            },
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }


def fixed_color(color: str) -> dict[str, str]:
    """
    Returns a color setting that gives a field one color.
    """
    return {"mode": "fixed", "fixedColor": color}
