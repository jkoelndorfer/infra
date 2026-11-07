"""
projects.homelab.monitoring.dashboards.vpn
==========================================

This module defines a Grafana dashboard of the WireGuard VPN that homelab.vpn
provisions: how many peers are connected, each peer's traffic, latest handshake and
endpoint, and wg-easy's web interface and logs. The metrics come from wg-easy,
through the job that `projects.homelab.monitoring.vpn_metrics` defines. The web
interface's requests come from Traefik, and the logs from Fluent Bit.
"""

from typing import Any

from infralib import DeploymentContext

from ...vpn import HomelabVPNProject
from ..fluent_bit import CONTAINER_FIELD, NAMESPACE_FIELD
from ..traefik_metrics import CODE_CLASS_LABEL, NAMESPACE_LABEL
from ..vpn_metrics import CONNECTED_HANDSHAKE_SECONDS, JOB_NAME
from .common import (
    DATASOURCE,
    Dashboard,
    color_text,
    column,
    legend_var,
    logs,
    row,
    stat,
    table,
    target,
    timeseries,
    value_mappings,
)

UID = "homelab-vpn"

_RATE_INTERVAL = "$__rate_interval"

_JOB = f'job="{JOB_NAME}"'
_PEERS = f'{_JOB},name=~"$peer"'

# wg-easy reports 0 for a peer that has never completed a handshake.
_HANDSHAKE = f"wireguard_latest_handshake_seconds{{{_PEERS}}}"
_HANDSHAKE_SEEN = f"({_HANDSHAKE} > 0)"

_PEER_GROUP = "max by (name, ipv4Address, enabled)"

_CONNECTED_STATUSES = {1: ("connected", "green"), 0: ("disconnected", "text")}
_ENABLED_STATUSES = {"true": ("yes", "green"), "false": ("no", "text")}
_UP_STATUSES = {1: ("up", "green"), 0: ("down", "red")}


def vpn_dashboard(dctx: DeploymentContext) -> Dashboard:
    """
    Returns the VPN dashboard.
    """
    vpn_namespace = HomelabVPNProject.metrics_endpoint(dctx).namespace
    panels = [
        row("Overview", y=0),
        *_overview_stats(y=1),
        _peer_counts({"h": 8, "w": 12, "x": 0, "y": 5}),
        _handshakes({"h": 8, "w": 12, "x": 12, "y": 5}),
        row("Peers", y=13),
        _traffic(
            "Received from peers",
            "Bits per second that wg-easy received from each peer.",
            "wireguard_received_bytes",
            {"h": 8, "w": 12, "x": 0, "y": 14},
        ),
        _traffic(
            "Sent to peers",
            "Bits per second that wg-easy sent to each peer.",
            "wireguard_sent_bytes",
            {"h": 8, "w": 12, "x": 12, "y": 14},
        ),
        _peers_table({"h": 10, "w": 16, "x": 0, "y": 22}),
        _endpoints_table({"h": 10, "w": 8, "x": 16, "y": 22}),
        row("Web interface", y=32),
        _web_requests(vpn_namespace, {"h": 10, "w": 12, "x": 0, "y": 33}),
        logs(
            "wg-easy logs",
            "The logs of wg-easy's pod, each line led by its container.",
            f'_stream:{{{NAMESPACE_FIELD}="{vpn_namespace}"}} '
            f'| format "<{CONTAINER_FIELD}>: <_msg>" as _msg',
            {"h": 10, "w": 12, "x": 12, "y": 33},
        ),
    ]
    for i, panel in enumerate(panels, start=1):
        panel["id"] = i

    return {
        "uid": UID,
        "title": "VPN",
        "description": (
            "The WireGuard VPN's peers, their traffic and handshakes, and wg-easy's "
            "web interface and logs."
        ),
        "tags": ["vpn", "wireguard"],
        "editable": True,
        "graphTooltip": 1,
        "schemaVersion": 39,
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "1m",
        "timezone": "browser",
        "templating": {"list": [_peer_variable()]},
        "annotations": {"list": []},
        "links": [],
        "panels": panels,
    }


def _peer_variable() -> dict[str, Any]:
    query = f"label_values(wireguard_sent_bytes{{{_JOB}}}, name)"
    return {
        "name": "peer",
        "label": "Peer",
        "type": "query",
        "datasource": dict(DATASOURCE),
        "query": {"query": query, "refId": "peer"},
        "definition": query,
        "refresh": 2,
        "sort": 1,
        "multi": True,
        "includeAll": True,
        # Matches peers that appear after the dashboard loads, too.
        "allValue": ".+",
        "current": {"selected": True, "text": ["All"], "value": ["$__all"]},
    }


def _overview_stats(y: int) -> list[dict[str, Any]]:
    stats = [
        stat(
            "Connected peers",
            f"Peers whose latest handshake was less than "
            f"{CONNECTED_HANDSHAKE_SECONDS // 60} minutes ago.",
            f"sum(wireguard_connected_peers{{{_JOB}}})",
            "short",
            x=0,
            y=y,
            decimals=0,
        ),
        stat(
            "Enabled peers",
            "Peers that are enabled, and so may connect.",
            f"sum(wireguard_enabled_peers{{{_JOB}}})",
            "short",
            x=6,
            y=y,
            decimals=0,
        ),
        stat(
            "Configured peers",
            "Peers that are configured, whether enabled or not.",
            f"sum(wireguard_configured_peers{{{_JOB}}})",
            "short",
            x=12,
            y=y,
            decimals=0,
        ),
        stat(
            "Metrics",
            "Whether VictoriaMetrics could scrape wg-easy's metrics. If it is down, "
            "check that Prometheus metrics are enabled in wg-easy, with homelab.vpn's "
            "metrics password.",
            f"min(up{{{_JOB}}})",
            "none",
            x=18,
            y=y,
        ),
    ]
    stats[-1]["fieldConfig"]["defaults"]["mappings"] = value_mappings(_UP_STATUSES)[
        "value"
    ]
    return stats


def _peer_counts(grid_pos: dict[str, int]) -> dict[str, Any]:
    targets = [
        target(f"sum(wireguard_{metric}_peers{{{_JOB}}})", legend=metric, ref_id=r)
        for metric, r in [("connected", "A"), ("enabled", "B"), ("configured", "C")]
    ]
    panel = timeseries(
        "Peers",
        "Peers that are connected, enabled and configured.",
        targets,
        grid_pos,
        "short",
        stacked=False,
        fill_opacity=0,
    )
    panel["fieldConfig"]["defaults"]["decimals"] = 0
    return panel


def _handshakes(grid_pos: dict[str, int]) -> dict[str, Any]:
    panel = timeseries(
        "Time since latest handshake",
        "Seconds since each peer's latest handshake. A peer counts as connected "
        f"below the line, at {CONNECTED_HANDSHAKE_SECONDS // 60} minutes. Peers that "
        "have never completed a handshake are not shown.",
        [target(f"max by (name) {_HANDSHAKE_SEEN}", legend=legend_var("name"))],
        grid_pos,
        "s",
        stacked=False,
        fill_opacity=0,
    )
    defaults = panel["fieldConfig"]["defaults"]
    defaults["thresholds"] = {
        "mode": "absolute",
        "steps": [
            {"color": "green", "value": None},
            {"color": "orange", "value": CONNECTED_HANDSHAKE_SECONDS},
        ],
    }
    defaults["custom"]["thresholdsStyle"] = {"mode": "line"}
    return panel


def _traffic(
    title: str, description: str, metric: str, grid_pos: dict[str, int]
) -> dict[str, Any]:
    return timeseries(
        title,
        description,
        [
            target(
                f"sum by (name) (rate({metric}{{{_PEERS}}}[{_RATE_INTERVAL}])) * 8",
                legend=legend_var("name"),
            )
        ],
        grid_pos,
        "bps",
    )


def _peers_table(grid_pos: dict[str, int]) -> dict[str, Any]:
    """
    Returns a table with a row per peer: whether it is enabled and connected, when
    its latest handshake was, and its traffic over the time range.
    """
    connected = (
        f"({_HANDSHAKE} > bool 0) * ({_HANDSHAKE} < bool {CONNECTED_HANDSHAKE_SECONDS})"
    )
    columns = {
        "Status": connected,
        "Latest handshake": _HANDSHAKE_SEEN,
        "Received": f"increase(wireguard_received_bytes{{{_PEERS}}}[$__range])",
        "Sent": f"increase(wireguard_sent_bytes{{{_PEERS}}}[$__range])",
    }
    bytes_column = [
        {"id": "unit", "value": "bytes"},
        {"id": "noValue", "value": "0"},
    ]
    return table(
        "Peers",
        "Each peer's address, whether it is enabled and connected, how long ago its "
        "latest handshake was, and the bytes received from and sent to it over the "
        "dashboard's time range.",
        {name: f"{_PEER_GROUP} ({expr})" for name, expr in columns.items()},
        {"name": "Peer", "ipv4Address": "Address", "enabled": "Enabled"},
        grid_pos,
        [
            column("Enabled", [value_mappings(_ENABLED_STATUSES), color_text()]),
            column("Status", [value_mappings(_CONNECTED_STATUSES), color_text()]),
            column(
                "Latest handshake",
                [
                    {"id": "unit", "value": "s"},
                    {"id": "noValue", "value": "never"},
                ],
            ),
            column("Received", bytes_column),
            column("Sent", bytes_column),
        ],
        sort_by="Peer",
    )


def _endpoints_table(grid_pos: dict[str, int]) -> dict[str, Any]:
    """
    Returns a table of the address that each peer last connected from.
    """
    return table(
        "Endpoints",
        "The public address and port that each peer last connected from.",
        {
            "Info": (
                f"max by (name, endpoint) (wireguard_peer_endpoint_info{{{_PEERS}}})"
            )
        },
        {"name": "Peer", "endpoint": "Endpoint"},
        grid_pos,
        # The query's value is always 1, so only its labels are worth showing.
        [column("Info", [{"id": "custom.hidden", "value": True}])],
        sort_by="Peer",
    )


def _web_requests(namespace: str, grid_pos: dict[str, int]) -> dict[str, Any]:
    return timeseries(
        "Web interface requests",
        "Requests per second to wg-easy's web interface through Traefik, by status "
        "class.",
        [
            target(
                f"sum by ({CODE_CLASS_LABEL}) (rate(traefik_service_requests_total"
                f'{{{NAMESPACE_LABEL}="{namespace}"}}[{_RATE_INTERVAL}]))',
                legend=legend_var(CODE_CLASS_LABEL),
            )
        ],
        grid_pos,
        "reqps",
    )
