"""
projects.homelab.monitoring.dashboards.common
=============================================

This module contains definitions shared by Grafana dashboards.
"""

from collections.abc import Callable
from string import ascii_uppercase
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

LOGS_DATASOURCE_UID = "victorialogs"
"""
The UID of the provisioned VictoriaLogs data source.
"""

LOGS_DATASOURCE = {
    "type": "victoriametrics-logs-datasource",
    "uid": LOGS_DATASOURCE_UID,
}
"""
A reference to the provisioned VictoriaLogs data source, for panels and queries.
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
    datasource: dict[str, str] = DATASOURCE,
) -> dict[str, Any]:
    """
    Returns a graph of the series that targets return, from zero, with a legend of
    each one's mean and maximum. The targets query datasource.
    """
    return {
        "type": "timeseries",
        "title": title,
        "description": description,
        "datasource": dict(datasource),
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


def column(name: str, properties: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Returns a field override that sets properties of the field (or table column)
    with the given display name.
    """
    return {"matcher": {"id": "byName", "options": name}, "properties": properties}


def color_text() -> dict[str, Any]:
    """
    Returns a property that colors a table cell's text by its value.
    """
    return {"id": "custom.cellOptions", "value": {"type": "color-text"}}


def value_mappings[K: int | str](mappings: dict[K, tuple[str, str]]) -> dict[str, Any]:
    """
    Returns a property that shows each value as text in a color, from a mapping of
    value to (text, color).
    """
    return {
        "id": "mappings",
        "value": [
            {
                "type": "value",
                "options": {
                    str(value): {"text": text, "color": color, "index": i}
                    for i, (value, (text, color)) in enumerate(mappings.items())
                },
            }
        ],
    }


def table(
    title: str,
    description: str,
    columns: dict[str, str],
    labels: dict[str, str],
    grid_pos: dict[str, int],
    overrides: list[dict[str, Any]],
    sort_by: str,
) -> dict[str, Any]:
    """
    Returns a table with a row per distinct set of labels. Each query in columns,
    keyed by column name, is an instant query whose result fills its column, and
    each must return the labels in labels, which maps a label to its column name.
    The label columns come first, in order, and rows are sorted by sort_by.
    """
    ref_ids = ascii_uppercase[: len(columns)]
    targets = [
        target(expr, legend=name, ref_id=ref_id, instant=True)
        for (name, expr), ref_id in zip(columns.items(), ref_ids)
    ]
    rename = {f"Value #{r}": name for name, r in zip(columns, ref_ids)}
    rename |= labels
    order = [*labels, *[f"Value #{r}" for r in ref_ids]]

    return {
        "type": "table",
        "title": title,
        "description": description,
        "datasource": dict(DATASOURCE),
        "gridPos": grid_pos,
        "targets": targets,
        "transformations": [
            {"id": "merge", "options": {}},
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"Time": True},
                    "indexByName": {c: i for i, c in enumerate(order)},
                    "renameByName": rename,
                },
            },
        ],
        "fieldConfig": {
            "defaults": {
                "custom": {"align": "auto", "cellOptions": {"type": "auto"}},
            },
            "overrides": overrides,
        },
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
            "sortBy": [{"displayName": sort_by, "desc": False}],
        },
    }


def logs_target(
    query: str,
    query_type: str,
    ref_id: str = "A",
    legend: str | None = None,
) -> dict[str, Any]:
    """
    Returns a LogsQL query [1] of the VictoriaLogs data source. An instant query
    returns log lines. A statsRange query returns the series of a query that ends in
    a stats pipe, at a step that Grafana picks from the time range, each series named
    by legend.

    [1]: https://docs.victoriametrics.com/victorialogs/logsql/
    """
    result: dict[str, Any] = {
        "datasource": dict(LOGS_DATASOURCE),
        "editorMode": "code",
        "expr": query,
        "queryType": query_type,
        "refId": ref_id,
    }
    if legend is not None:
        result["legendFormat"] = legend
    return result


def logs(
    title: str,
    description: str,
    query: str,
    grid_pos: dict[str, int],
) -> dict[str, Any]:
    """
    Returns a panel of the logs that a LogsQL query [1] matches, newest first. Grafana
    colors each line by its level field.

    [1]: https://docs.victoriametrics.com/victorialogs/logsql/
    """
    return {
        "type": "logs",
        "title": title,
        "description": description,
        "datasource": dict(LOGS_DATASOURCE),
        "gridPos": grid_pos,
        "targets": [logs_target(query, "instant")],
        "options": {
            "showTime": True,
            "showLabels": False,
            "showCommonLabels": False,
            "wrapLogMessage": True,
            "prettifyLogMessage": False,
            "enableLogDetails": True,
            "dedupStrategy": "none",
            "sortOrder": "Descending",
        },
    }
