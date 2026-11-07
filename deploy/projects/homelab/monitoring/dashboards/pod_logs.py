"""
projects.homelab.monitoring.dashboards.pod_logs
===============================================

This module defines a Grafana dashboard of the Kubernetes pods' logs: how many lines
each namespace and pod logs, the lines that mention errors, and the lines themselves,
narrowed by namespace, pod, container and a LogsQL filter. The logs come from Fluent
Bit, through the fields that `projects.homelab.monitoring.fluent_bit` defines.
"""

from typing import Any

from infralib import DeploymentContext

from ..fluent_bit import CONTAINER_FIELD, NAMESPACE_FIELD, POD_FIELD
from .common import (
    LOGS_DATASOURCE,
    Dashboard,
    legend_vars,
    logs,
    logs_target,
    row,
    timeseries,
)

UID = "homelab-pod-logs"

# Only the pods' logs have a namespace, which keeps out the syslog that VictoriaLogs
# also holds. As a stream filter, it skips the syslog's blocks without reading them.
_PODS = f'_stream:{{{NAMESPACE_FIELD}=~".+"}}'

# The plugin turns `field:=$var` into `field:in(...)` with the selected values, and
# into `field:in(*)`, which matches every line, for All [1]. The search is wrapped in
# parentheses so that an `or` in it cannot escape the other filters. That makes an
# empty search a syntax error, so it defaults to `*`.
#
# [1]: https://github.com/VictoriaMetrics/victorialogs-datasource/blob/main/CHANGELOG.md
_NAMESPACE = f"{NAMESPACE_FIELD}:=$namespace"
_POD = f"{POD_FIELD}:=$pod"
_CONTAINER = f"{CONTAINER_FIELD}:=$container"
_SELECTED = f"{_PODS} {_NAMESPACE} {_POD} {_CONTAINER} ($search)"

_ERRORS = "(i(error) or i(fatal) or i(panic))"
"""
A filter of the lines that mention an error, by word and regardless of case. It is a
guess, because the pods do not log in a common format.
"""

_ERRORS_DESCRIPTION = (
    'Lines that contain the word "error", "fatal" or "panic", in any case.'
)


def pod_logs_dashboard(dctx: DeploymentContext) -> Dashboard:
    """
    Returns the pod logs dashboard.
    """
    panels = [
        row("Volume", y=0),
        _lines_by(
            "Lines by namespace",
            "Lines logged per step, by namespace.",
            _SELECTED,
            [NAMESPACE_FIELD],
            {"h": 8, "w": 12, "x": 0, "y": 1},
        ),
        _lines_by(
            "Lines by pod",
            "Lines logged per step, by pod.",
            _SELECTED,
            [NAMESPACE_FIELD, POD_FIELD],
            {"h": 8, "w": 12, "x": 12, "y": 1},
        ),
        row("Errors", y=9),
        _lines_by(
            "Error lines by pod",
            f"{_ERRORS_DESCRIPTION} Per step, by pod.",
            f"{_SELECTED} {_ERRORS}",
            [NAMESPACE_FIELD, POD_FIELD],
            {"h": 10, "w": 12, "x": 0, "y": 10},
        ),
        logs(
            "Error lines",
            _ERRORS_DESCRIPTION,
            _with_source(f"{_SELECTED} {_ERRORS}"),
            {"h": 10, "w": 12, "x": 12, "y": 10},
        ),
        row("Logs", y=20),
        logs(
            "Logs",
            "The selected containers' lines, each led by its pod and container.",
            _with_source(_SELECTED),
            {"h": 24, "w": 24, "x": 0, "y": 21},
        ),
    ]
    for i, panel in enumerate(panels, start=1):
        panel["id"] = i

    return {
        "uid": UID,
        "title": "Pod logs",
        "description": (
            "The Kubernetes pods' logs, by namespace, pod and container, and how "
            "many lines each logs."
        ),
        "tags": ["kubernetes", "logs"],
        "editable": True,
        "graphTooltip": 1,
        "schemaVersion": 39,
        "time": {"from": "now-1h", "to": "now"},
        "refresh": "1m",
        "timezone": "browser",
        "templating": {
            "list": [
                _field_variable("namespace", "Namespace", NAMESPACE_FIELD, _PODS),
                _field_variable("pod", "Pod", POD_FIELD, f"{_PODS} {_NAMESPACE}"),
                _field_variable(
                    "container",
                    "Container",
                    CONTAINER_FIELD,
                    f"{_PODS} {_NAMESPACE} {_POD}",
                ),
                {
                    "name": "search",
                    "label": "Search",
                    "description": (
                        "A LogsQL filter of the lines, such as a word, a quoted "
                        'phrase or `~"regexp"`. `*` matches every line; an empty '
                        "search is an error."
                    ),
                    "type": "textbox",
                    "query": "*",
                    "current": {"text": "*", "value": "*"},
                },
            ]
        },
        "annotations": {"list": []},
        "links": [],
        "panels": panels,
    }


def _field_variable(name: str, label: str, field: str, query: str) -> dict[str, Any]:
    """
    Returns a variable of the values that field takes in the logs that query matches,
    over the dashboard's time range.
    """
    variable_query = {
        "type": "fieldValue",
        "field": field,
        "query": query,
        "limit": 1000,
        "refId": name,
    }
    return {
        "name": name,
        "label": label,
        "type": "query",
        "datasource": dict(LOGS_DATASOURCE),
        "query": variable_query,
        "definition": query,
        "refresh": 2,
        "sort": 1,
        "multi": True,
        "includeAll": True,
        # Matches values that appear after the dashboard loads, too.
        "allValue": "*",
        "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
    }


def _with_source(query: str) -> str:
    """
    Returns query with each line led by its pod and container.
    """
    return f'{query} | format "<{POD_FIELD}>/<{CONTAINER_FIELD}>: <_msg>" as _msg'


def _lines_by(
    title: str,
    description: str,
    query: str,
    fields: list[str],
    grid_pos: dict[str, int],
) -> dict[str, Any]:
    by = ", ".join(fields)
    return timeseries(
        title,
        description,
        [
            logs_target(
                f"{query} | stats by ({by}) count() as lines",
                "statsRange",
                legend=legend_vars(*fields, sep="/"),
            )
        ],
        grid_pos,
        "short",
        datasource=LOGS_DATASOURCE,
    )
