"""
projects.homelab.monitoring.dashboards.network
==============================================

This module defines a Grafana dashboard of the router and switches: traffic,
errors and status by interface, and the router's CPU, memory, load and storage.
The metrics come from the SNMP exporter, through the jobs that
`projects.homelab.monitoring.snmp_exporter` defines.
"""

from typing import Any

from infralib import DeploymentContext

from ..snmp_exporter import JOB_PREFIX, ROUTER_NAME
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

UID = "homelab-network"

_RATE_INTERVAL = "$__rate_interval"

_SNMP = f'job=~"{JOB_PREFIX}.+"'
_DEVICES = f'{_SNMP},instance=~"$device"'
_INTERFACES = f'{_DEVICES},ifName=~"$interface"'
_ROUTER = f'{_SNMP},instance="{ROUTER_NAME}"'

# Interfaces are kept only while they are up, so that the many unused switch ports
# and router interfaces stay out of the graphs.
_UP = "and on (instance, ifIndex) ifOperStatus == 1"

_INTERFACE_LEGEND = legend_vars("instance", "ifName")

# The CPU time counters that add up to the router's total. On Linux, the system
# counter already includes time spent on interrupts.
_CPU_MODES = {
    "user": "ssCpuRawUser",
    "nice": "ssCpuRawNice",
    "system": "ssCpuRawSystem",
    "wait": "ssCpuRawWait",
    "idle": "ssCpuRawIdle",
}

# ifOperStatus values [1].
#
# [1]: https://www.rfc-editor.org/rfc/rfc2863#section-6
_OPER_STATUSES = {
    1: ("up", "green"),
    2: ("down", "red"),
    3: ("testing", "orange"),
    4: ("unknown", "gray"),
    5: ("dormant", "blue"),
    6: ("notPresent", "gray"),
    7: ("lowerLayerDown", "red"),
}


def network_dashboard(dctx: DeploymentContext) -> Dashboard:
    """
    Returns the network dashboard.
    """
    panels = [
        row("Overview", y=0),
        *_overview_stats(y=1),
        _traffic("Receive", "ifHCInOctets", {"h": 8, "w": 12, "x": 0, "y": 5}),
        _traffic("Transmit", "ifHCOutOctets", {"h": 8, "w": 12, "x": 12, "y": 5}),
        _interfaces_table(y=13),
        row("Errors", y=23),
        _interface_problems(
            "Errors",
            "Packets per second that could not be received or sent because of errors.",
            "ifInErrors",
            "ifOutErrors",
            {"h": 8, "w": 12, "x": 0, "y": 24},
        ),
        _interface_problems(
            "Discards",
            "Packets per second discarded without errors, such as to free buffer "
            "space.",
            "ifInDiscards",
            "ifOutDiscards",
            {"h": 8, "w": 12, "x": 12, "y": 24},
        ),
        row(f"Router ({ROUTER_NAME})", y=32),
        _router_cpu({"h": 8, "w": 12, "x": 0, "y": 33}),
        _router_memory({"h": 8, "w": 12, "x": 12, "y": 33}),
        timeseries(
            "Load average",
            "The router's load averages.",
            [target(f"laLoadFloat{{{_ROUTER}}}", legend=legend_var("laNames"))],
            {"h": 8, "w": 12, "x": 0, "y": 41},
            "short",
            stacked=False,
            fill_opacity=0,
        ),
        _router_storage({"h": 8, "w": 12, "x": 12, "y": 41}),
    ]
    for i, panel in enumerate(panels, start=1):
        panel["id"] = i

    return {
        "uid": UID,
        "title": "Network",
        "description": (
            "Traffic, errors and status of the router's and switches' interfaces, "
            "and the router's resources."
        ),
        "tags": ["network", "snmp"],
        "editable": True,
        "graphTooltip": 1,
        "schemaVersion": 39,
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "1m",
        "timezone": "browser",
        "templating": {
            "list": [
                _variable(
                    "device",
                    "Device",
                    f"label_values(ifOperStatus{{{_SNMP}}}, instance)",
                ),
                _variable(
                    "interface",
                    "Interface",
                    f"label_values(ifOperStatus{{{_DEVICES}}}, ifName)",
                ),
            ]
        },
        "annotations": {"list": []},
        "links": [],
        "panels": panels,
    }


def _variable(name: str, label: str, query: str) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "type": "query",
        "datasource": dict(DATASOURCE),
        "query": {"query": query, "refId": name},
        "definition": query,
        "refresh": 2,
        "sort": 1,
        "multi": True,
        "includeAll": True,
        # Matches values that appear after the dashboard loads, too.
        "allValue": ".+",
        "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
    }


def _rate(metric: str, selector: str) -> str:
    return f"rate({metric}{{{selector}}}[{_RATE_INTERVAL}])"


def _cpu_total() -> str:
    return " + ".join(_rate(m, _ROUTER) for m in _CPU_MODES.values())


def _memory_used() -> str:
    """
    Returns the router's memory in use, in kilobytes, as UCD reports memory. Buffers
    and caches are not counted, because the kernel frees them as needed.
    """
    return (
        f"memTotalReal{{{_ROUTER}}} - memAvailReal{{{_ROUTER}}} "
        f"- memBuffer{{{_ROUTER}}} - memCached{{{_ROUTER}}}"
    )


def _overview_stats(y: int) -> list[dict[str, Any]]:
    idle = " + ".join(_rate(_CPU_MODES[m], _ROUTER) for m in ["idle", "wait"])
    return [
        stat(
            "Uptime",
            "How long each device's SNMP agent has been running.",
            # sysUpTime is in hundredths of a second.
            f"sysUpTime{{{_DEVICES}}} / 100",
            "s",
            x=0,
            y=y,
            legend=legend_var("instance"),
        ),
        stat(
            "Router CPU",
            "The share of the router's CPU time spent busy.",
            f"1 - ({idle}) / ({_cpu_total()})",
            "percentunit",
            x=6,
            y=y,
            thresholds=[
                {"color": "green", "value": None},
                {"color": "orange", "value": 0.75},
                {"color": "red", "value": 0.9},
            ],
        ),
        stat(
            "Router memory",
            "The share of the router's memory in use, leaving out buffers and caches.",
            f"({_memory_used()}) / memTotalReal{{{_ROUTER}}}",
            "percentunit",
            x=12,
            y=y,
            thresholds=[
                {"color": "green", "value": None},
                {"color": "orange", "value": 0.8},
                {"color": "red", "value": 0.9},
            ],
        ),
        stat(
            "Interfaces up",
            "The number of each device's interfaces that are up.",
            f"count by (instance) (ifOperStatus{{{_DEVICES}}} == 1)",
            "short",
            x=18,
            y=y,
            decimals=0,
            legend=legend_var("instance"),
        ),
    ]


def _traffic(direction: str, metric: str, grid_pos: dict[str, int]) -> dict[str, Any]:
    return timeseries(
        direction,
        "Bits per second, by interface. Only interfaces that are up are shown.",
        [target(f"{_rate(metric, _INTERFACES)} * 8 {_UP}", _INTERFACE_LEGEND)],
        grid_pos,
        "bps",
        stacked=False,
        fill_opacity=10,
    )


def _interface_problems(
    title: str,
    description: str,
    in_metric: str,
    out_metric: str,
    grid_pos: dict[str, int],
) -> dict[str, Any]:
    targets = [
        target(
            f"{_rate(metric, _INTERFACES)} > 0",
            legend=f"{_INTERFACE_LEGEND} {direction}",
            ref_id=ref_id,
        )
        for metric, direction, ref_id in [
            (in_metric, "in", "A"),
            (out_metric, "out", "B"),
        ]
    ]
    return timeseries(
        title,
        f"{description} Only interfaces with any are shown.",
        targets,
        grid_pos,
        "pps",
        stacked=False,
        fill_opacity=10,
    )


def _interfaces_table(y: int) -> dict[str, Any]:
    """
    Returns a table with a row per interface: its status and speed, its current
    traffic, and its errors and discards over the time range.
    """
    group = "max by (instance, ifName, ifAlias)"
    columns = {
        "Status": f"ifOperStatus{{{_INTERFACES}}}",
        "Speed": f"ifHighSpeed{{{_INTERFACES}}} * 1000000",
        "Receive": f"{_rate('ifHCInOctets', _INTERFACES)} * 8",
        "Transmit": f"{_rate('ifHCOutOctets', _INTERFACES)} * 8",
        "Errors": (
            f"increase(ifInErrors{{{_INTERFACES}}}[$__range]) "
            f"+ increase(ifOutErrors{{{_INTERFACES}}}[$__range])"
        ),
        "Discards": (
            f"increase(ifInDiscards{{{_INTERFACES}}}[$__range]) "
            f"+ increase(ifOutDiscards{{{_INTERFACES}}}[$__range])"
        ),
    }
    ref_ids = "ABCDEF"
    targets = [
        target(f"{group} ({expr})", legend=name, ref_id=ref_id, instant=True)
        for (name, expr), ref_id in zip(columns.items(), ref_ids)
    ]
    rename = {f"Value #{r}": name for name, r in zip(columns, ref_ids)}
    rename |= {"instance": "Device", "ifName": "Interface", "ifAlias": "Description"}
    order = ["instance", "ifName", "ifAlias", *[f"Value #{r}" for r in ref_ids]]

    return {
        "type": "table",
        "title": "Interfaces",
        "description": (
            "Each interface's status and speed, its current traffic, and its errors "
            "and discards over the dashboard's time range."
        ),
        "datasource": dict(DATASOURCE),
        "gridPos": {"h": 10, "w": 24, "x": 0, "y": y},
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
            "overrides": [
                _column("Status", [_status_mappings(), _color_text()]),
                _column("Speed", [{"id": "unit", "value": "bps"}]),
                _column("Receive", [{"id": "unit", "value": "bps"}]),
                _column("Transmit", [{"id": "unit", "value": "bps"}]),
                *[
                    _column(
                        name,
                        [
                            {"id": "unit", "value": "short"},
                            {"id": "decimals", "value": 0},
                            {"id": "noValue", "value": "0"},
                        ],
                    )
                    for name in ["Errors", "Discards"]
                ],
            ],
        },
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
            "sortBy": [{"displayName": "Device", "desc": False}],
        },
    }


def _column(name: str, properties: list[dict[str, Any]]) -> dict[str, Any]:
    return {"matcher": {"id": "byName", "options": name}, "properties": properties}


def _status_mappings() -> dict[str, Any]:
    return {
        "id": "mappings",
        "value": [
            {
                "type": "value",
                "options": {
                    str(value): {"text": text, "color": color, "index": i}
                    for i, (value, (text, color)) in enumerate(_OPER_STATUSES.items())
                },
            }
        ],
    }


def _color_text() -> dict[str, Any]:
    return {"id": "custom.cellOptions", "value": {"type": "color-text"}}


def _router_cpu(grid_pos: dict[str, int]) -> dict[str, Any]:
    total = _cpu_total()
    targets = [
        target(f"{_rate(metric, _ROUTER)} / ({total})", legend=mode, ref_id=ref_id)
        for (mode, metric), ref_id in zip(_CPU_MODES.items(), "ABCDE")
        if mode != "idle"
    ]
    return timeseries(
        "CPU",
        "The share of the router's CPU time spent in each mode, other than idle.",
        targets,
        grid_pos,
        "percentunit",
    )


def _router_memory(grid_pos: dict[str, int]) -> dict[str, Any]:
    # UCD reports memory in kilobytes.
    parts = {
        "used": _memory_used(),
        "buffers": f"memBuffer{{{_ROUTER}}}",
        "cached": f"memCached{{{_ROUTER}}}",
        "free": f"memAvailReal{{{_ROUTER}}}",
    }
    targets = [
        target(f"({expr}) * 1024", legend=name, ref_id=ref_id)
        for (name, expr), ref_id in zip(parts.items(), "ABCD")
    ]
    return timeseries(
        "Memory",
        "The router's memory, by use.",
        targets,
        grid_pos,
        "bytes",
        overrides=[
            _column("free", [{"id": "color", "value": fixed_color("green")}]),
        ],
    )


def _router_storage(grid_pos: dict[str, int]) -> dict[str, Any]:
    # Memory is reported as storage too. Pseudo filesystems report no size.
    selector = f'{_ROUTER},hrStorageDescr!~"(?i).*(memory|swap).*"'
    return timeseries(
        "Storage",
        "The share of each of the router's filesystems in use.",
        [
            target(
                f"hrStorageUsed{{{selector}}} / (hrStorageSize{{{selector}}} > 0)",
                legend=legend_var("hrStorageDescr"),
            )
        ],
        grid_pos,
        "percentunit",
        stacked=False,
        fill_opacity=0,
    )
