"""
projects.homelab.monitoring.dashboards.traefik
==============================================

This module defines a Grafana dashboard of requests through Traefik, by namespace,
deployment, and status class. The labels it groups by come from
`projects.homelab.monitoring.traefik_metrics`.
"""

from typing import Any

from infralib import DeploymentContext

from ..traefik_metrics import (
    CODE_CLASS_LABEL,
    DEPLOYMENT_LABEL,
    NAMESPACE_LABEL,
    OTHER_CODE_CLASS,
)
from .common import (
    DATASOURCE,
    Dashboard,
    fixed_color,
    legend_var,
    legend_vars,
    row,
    stat,
    target,
    timeseries,
)

UID = "homelab-traefik"

_METRIC = "traefik_service_requests_total"
_SELECTED = f'{NAMESPACE_LABEL}=~"$namespace"'
_RATE_INTERVAL = "$__rate_interval"

_STATUS_CLASSES = ["2xx", "3xx", "4xx", "5xx"]
_CODE_CLASS_COLORS = {
    "1xx": "text",
    OTHER_CODE_CLASS: "gray",
    "2xx": "green",
    "3xx": "blue",
    "4xx": "orange",
    "5xx": "red",
}


def traefik_dashboard(dctx: DeploymentContext) -> Dashboard:
    """
    Returns the Traefik dashboard.
    """
    panels = [
        row("Overview", y=0),
        *_overview_stats(y=1),
        _timeseries(
            "Requests by status class",
            "Requests per second, by status class.",
            _rate_by(CODE_CLASS_LABEL),
            legend_var(CODE_CLASS_LABEL),
            {"h": 8, "w": 12, "x": 0, "y": 5},
            _code_class_overrides("^{}$"),
        ),
        _timeseries(
            "Requests by namespace",
            "Requests per second, by namespace.",
            _rate_by(NAMESPACE_LABEL),
            legend_var(NAMESPACE_LABEL),
            {"h": 8, "w": 12, "x": 12, "y": 5},
        ),
        _requests_table(y=13),
        {**row("$namespace", y=23), "repeat": "namespace"},
        _timeseries(
            "Requests by deployment and status class",
            "Requests per second to each deployment in the namespace, by status class.",
            f"sum by ({DEPLOYMENT_LABEL}, {CODE_CLASS_LABEL}) "
            f'(rate({_METRIC}{{{NAMESPACE_LABEL}="$namespace"}}[{_RATE_INTERVAL}]))',
            legend_vars(DEPLOYMENT_LABEL, CODE_CLASS_LABEL),
            {"h": 8, "w": 24, "x": 0, "y": 24},
            _code_class_overrides(".* {}$"),
        ),
    ]
    for i, panel in enumerate(panels, start=1):
        panel["id"] = i

    return {
        "uid": UID,
        "title": "Traefik",
        "description": (
            "Requests through Traefik, by namespace, deployment, and status class."
        ),
        "tags": ["traefik"],
        "editable": True,
        "graphTooltip": 1,
        "schemaVersion": 39,
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "1m",
        "timezone": "browser",
        "templating": {"list": [_namespace_variable()]},
        "annotations": {"list": []},
        "links": [],
        "panels": panels,
    }


def _namespace_variable() -> dict[str, Any]:
    query = f"label_values({_METRIC}, {NAMESPACE_LABEL})"
    return {
        "name": "namespace",
        "label": "Namespace",
        "type": "query",
        "datasource": dict(DATASOURCE),
        "query": {"query": query, "refId": "namespace"},
        "definition": query,
        "refresh": 2,
        "sort": 1,
        "multi": True,
        "includeAll": True,
        # Matches namespaces that appear after the dashboard loads, too.
        "allValue": ".+",
        "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
    }


def _overview_stats(y: int) -> list[dict[str, Any]]:
    total = f"sum(rate({_METRIC}{{{_SELECTED}}}[{_RATE_INTERVAL}]))"
    stats = [
        stat(
            "Request rate",
            "Requests per second across the selected namespaces.",
            total,
            "reqps",
            x=0,
            y=y,
        ),
        stat(
            "Requests",
            "Requests across the selected namespaces, over the dashboard's time range.",
            f"sum(increase({_METRIC}{{{_SELECTED}}}[$__range]))",
            "short",
            x=6,
            y=y,
            decimals=0,
        ),
    ]
    # (orange, red) thresholds for the share of requests in each class.
    thresholds = {"4xx": (0.05, 0.25), "5xx": (0.01, 0.05)}
    for i, (code_class, (orange, red)) in enumerate(thresholds.items()):
        matching = (
            f'sum(rate({_METRIC}{{{_SELECTED},{CODE_CLASS_LABEL}="{code_class}"}}'
            f"[{_RATE_INTERVAL}]))"
        )
        stats.append(
            stat(
                f"{code_class} ratio",
                f"The share of requests that returned {code_class}.",
                f"{matching} / {total}",
                "percentunit",
                x=12 + 6 * i,
                y=y,
                thresholds=[
                    {"color": "green", "value": None},
                    {"color": "orange", "value": orange},
                    {"color": "red", "value": red},
                ],
            )
        )
    return stats


def _requests_table(y: int) -> dict[str, Any]:
    """
    Returns a table of requests over the time range, with a row per namespace and
    deployment, and a column per status class.
    """
    group = f"sum by ({NAMESPACE_LABEL}, {DEPLOYMENT_LABEL})"
    ref_ids = "ABCD"
    targets = [
        target(
            f"{group} (increase({_METRIC}{{{_SELECTED},"
            f'{CODE_CLASS_LABEL}="{code_class}"}}[$__range]))',
            legend=code_class,
            ref_id=ref_id,
            instant=True,
        )
        for code_class, ref_id in zip(_STATUS_CLASSES, ref_ids)
    ]
    targets.append(
        target(
            f"{group} (increase({_METRIC}{{{_SELECTED}}}[$__range]))",
            legend="Total",
            ref_id="E",
            instant=True,
        )
    )
    rename = {f"Value #{r}": c for c, r in zip(_STATUS_CLASSES, ref_ids)}
    rename["Value #E"] = "Total"
    columns = [NAMESPACE_LABEL, DEPLOYMENT_LABEL, *_STATUS_CLASSES, "Total"]

    return {
        "type": "table",
        "title": "Requests by namespace, deployment, and status class",
        "description": "Requests over the dashboard's time range.",
        "datasource": dict(DATASOURCE),
        "gridPos": {"h": 10, "w": 24, "x": 0, "y": y},
        "targets": targets,
        "transformations": [
            {"id": "merge", "options": {}},
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"Time": True},
                    "indexByName": {c: i for i, c in enumerate(columns)},
                    "renameByName": rename,
                },
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "short",
                "decimals": 0,
                "noValue": "0",
                "custom": {"align": "auto", "cellOptions": {"type": "auto"}},
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": c},
                    "properties": [
                        {"id": "custom.cellOptions", "value": {"type": "color-text"}},
                        {"id": "color", "value": fixed_color(_CODE_CLASS_COLORS[c])},
                    ],
                }
                for c in _STATUS_CLASSES
            ],
        },
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
            "sortBy": [{"displayName": NAMESPACE_LABEL, "desc": False}],
        },
    }


def _timeseries(
    title: str,
    description: str,
    expr: str,
    legend: str,
    grid_pos: dict[str, int],
    overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return timeseries(
        title, description, [target(expr, legend=legend)], grid_pos, "reqps", overrides
    )


def _rate_by(label: str) -> str:
    return f"sum by ({label}) (rate({_METRIC}{{{_SELECTED}}}[{_RATE_INTERVAL}]))"


def _code_class_overrides(display_name_regex: str) -> list[dict[str, Any]]:
    """
    Returns overrides that color each status class consistently. The regex format
    string receives the escaped class, and must match the series' display name.
    """
    return [
        {
            "matcher": {
                "id": "byRegexp",
                "options": display_name_regex.format(_regex_escape(code_class)),
            },
            "properties": [{"id": "color", "value": fixed_color(color)}],
        }
        for code_class, color in _CODE_CLASS_COLORS.items()
    ]


def _regex_escape(s: str) -> str:
    # Grafana matches with JavaScript regexes, so escape only the metacharacters
    # that class names contain, rather than use Python's re.escape.
    return s.replace("(", r"\(").replace(")", r"\)")
