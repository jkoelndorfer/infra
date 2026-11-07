"""
projects.homelab.monitoring.dashboards.blocky
=============================================

This module defines a Grafana dashboard of Blocky, the DNS server that
homelab.blocky provisions: how many queries it answers, how it answers them, and
how fast, and the domains that each client looks up. The query metrics come from
Blocky, through the job that `projects.homelab.monitoring.blocky_metrics` defines.
The lookups come from Blocky's query log, which Fluent Bit collects.

Blocky logs each query as a line of JSON. The lookups' panels unpack its fields when
they query, and the client and domain variables narrow them to the lookups that
match. Clicking a domain or client in a table narrows the dashboard to it.
"""

from typing import Any

from infralib import DeploymentContext

from ...blocky import HomelabBlockyProject
from ..blocky_metrics import JOB_NAME
from ..fluent_bit import NAMESPACE_FIELD
from .common import (
    LOGS_DATASOURCE,
    Dashboard,
    column,
    legend_var,
    logs,
    logs_table,
    logs_target,
    row,
    stat,
    target,
    timeseries,
    value_mappings,
)

UID = "homelab-blocky"

_RATE_INTERVAL = "$__rate_interval"

_JOB = f'job="{JOB_NAME}"'

# The fields of Blocky's query log [1]. Blocky leaves out fields that are empty or
# zero, such as the duration of a query that its cache answered.
#
# [1]: https://github.com/0xERR0R/blocky/blob/main/querylog/logger_writer.go
_CLIENT = "client_names"
_CLIENT_IP = "client_ip"
_DOMAIN = "question_name"
_QUERY_TYPE = "question_type"
_RESPONSE_TYPE = "response_type"
_RESPONSE_REASON = "response_reason"
_ANSWER = "answer"
_QUERY_FIELDS = [
    _CLIENT,
    _CLIENT_IP,
    _DOMAIN,
    _QUERY_TYPE,
    _RESPONSE_TYPE,
    _RESPONSE_REASON,
    _ANSWER,
]

# Blocky's JSON log lines [1] name their message msg, and their logger prefix, which
# is queryLog for the query log's lines.
#
# [1]: https://github.com/0xERR0R/blocky/blob/main/log/logger.go
_LEVEL = "level"
_MESSAGE = "msg"
_PREFIX = "prefix"
_ERROR = "error"
_QUERY_LOG_PREFIX = "queryLog"
_QUERY_LOG_MESSAGE = '"query resolved"'

_BLOCKED = "BLOCKED"
_CACHED = "CACHED"

_TOP = 20
"""
How many rows the tables of the most frequent domains and clients show.
"""

_BLOCKING_STATUSES = {1: ("enabled", "green"), 0: ("disabled", "red")}
_UP_STATUSES = {1: ("up", "green"), 0: ("down", "red")}


def blocky_dashboard(dctx: DeploymentContext) -> Dashboard:
    """
    Returns the Blocky dashboard.
    """
    stream = (
        f"_stream:{{{NAMESPACE_FIELD}="
        f'"{HomelabBlockyProject.metrics_endpoint(dctx).namespace}"}}'
    )
    # The phrase filter skips the other lines before unpacking, which is the costly
    # part. The variables are regular expressions, which match every value when
    # they are empty.
    lookups = (
        f"{stream} {_QUERY_LOG_MESSAGE} "
        f"| unpack_json fields ({', '.join([_LEVEL, _PREFIX, *_QUERY_FIELDS])}) "
        f"| filter {_PREFIX}:={_QUERY_LOG_PREFIX} "
        f'({_CLIENT}:~"$client" or {_CLIENT_IP}:~"$client") '
        f'{_DOMAIN}:~"$domain"'
    )
    blocked = f"{lookups} {_RESPONSE_TYPE}:={_BLOCKED}"

    panels = [
        row("Overview", y=0),
        *_overview_stats(y=1),
        row("Queries", y=9),
        _responses_by(
            "Responses by type",
            "Responses per second, by how Blocky answered: from its cache, by "
            "resolving upstream, by blocking, and so on.",
            "response_type",
            {"h": 8, "w": 12, "x": 0, "y": 10},
        ),
        timeseries(
            "Queries by client",
            "Queries per second, by client. Clients without a DHCP assignment are "
            "named by address.",
            [
                target(
                    f"sum by (client) (rate(blocky_query_total{{{_JOB}}}"
                    f"[{_RATE_INTERVAL}]))",
                    legend=legend_var("client"),
                )
            ],
            {"h": 8, "w": 12, "x": 12, "y": 10},
            "reqps",
        ),
        timeseries(
            "Queries by record type",
            "Queries per second, by the type of record asked for.",
            [
                target(
                    f"sum by (type) (rate(blocky_query_total{{{_JOB}}}"
                    f"[{_RATE_INTERVAL}]))",
                    legend=legend_var("type"),
                )
            ],
            {"h": 8, "w": 8, "x": 0, "y": 18},
            "reqps",
        ),
        _responses_by(
            "Responses by code",
            "Responses per second, by DNS response code. NXDOMAIN means that the "
            "domain does not exist.",
            "response_code",
            {"h": 8, "w": 8, "x": 8, "y": 18},
        ),
        _response_times({"h": 8, "w": 8, "x": 16, "y": 18}),
        row("Lookups", y=26),
        _top_domains(
            "Top domains",
            "The domains looked up most often by the selected clients, and how many "
            "clients looked each up. Click a domain to show only its lookups.",
            lookups,
            {"h": 10, "w": 8, "x": 0, "y": 27},
        ),
        _top_domains(
            "Top blocked domains",
            "The blocked domains looked up most often by the selected clients, and "
            "how many clients looked each up. Click a domain to show only its "
            "lookups.",
            blocked,
            {"h": 10, "w": 8, "x": 8, "y": 27},
        ),
        _top_clients(lookups, {"h": 10, "w": 8, "x": 16, "y": 27}),
        _lookups_by(
            "Lookups by client",
            "The selected lookups per step, by client.",
            lookups,
            _CLIENT,
            {"h": 8, "w": 12, "x": 0, "y": 37},
        ),
        _lookups_by(
            "Blocked lookups by domain",
            "The selected blocked lookups per step, by domain.",
            blocked,
            _DOMAIN,
            {"h": 8, "w": 12, "x": 12, "y": 37},
        ),
        logs(
            "Query log",
            "The selected lookups: the client, the record type and domain asked "
            "for, how Blocky answered, and its answer.",
            f'{lookups} | format "<{_CLIENT}>: <{_QUERY_TYPE}> <{_DOMAIN}> -> '
            f'<{_RESPONSE_REASON}> <{_ANSWER}>" as _msg',
            {"h": 16, "w": 24, "x": 0, "y": 45},
        ),
        row("Logs", y=61),
        logs(
            "Blocky logs",
            "Blocky's logs other than its query log, each line led by its logger. "
            "Neither variable applies to these.",
            f"{stream} -{_QUERY_LOG_MESSAGE} "
            f"| unpack_json fields ({_LEVEL}, {_PREFIX}, {_MESSAGE}, {_ERROR}) "
            f'| format if ({_MESSAGE}:*) "<{_MESSAGE}>" as _msg '
            f'| format if ({_ERROR}:*) "<_msg>: <{_ERROR}>" as _msg '
            f'| format if ({_PREFIX}:*) "<{_PREFIX}>: <_msg>" as _msg',
            {"h": 10, "w": 24, "x": 0, "y": 62},
        ),
    ]
    for i, panel in enumerate(panels, start=1):
        panel["id"] = i

    return {
        "uid": UID,
        "title": "DNS",
        "description": (
            "Blocky's DNS queries: how it answers them and how fast, and the domains "
            "that each client looks up."
        ),
        "tags": ["dns", "blocky"],
        "editable": True,
        "graphTooltip": 1,
        "schemaVersion": 39,
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "1m",
        "timezone": "browser",
        "templating": {
            "list": [
                _regexp_variable(
                    "client",
                    "Client",
                    "A regular expression of the clients' names or addresses whose "
                    "lookups to show. Empty shows every client's.",
                ),
                _regexp_variable(
                    "domain",
                    "Domain",
                    "A regular expression of the domains whose lookups to show. "
                    "Empty shows every domain's.",
                ),
            ]
        },
        "annotations": {"list": []},
        "links": [],
        "panels": panels,
    }


def _regexp_variable(name: str, label: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "description": description,
        "type": "textbox",
        "query": "",
        "current": {"text": "", "value": ""},
    }


def _overview_stats(y: int) -> list[dict[str, Any]]:
    def share(response_type: str) -> str:
        return (
            f"sum(rate(blocky_response_total{{{_JOB},"
            f'response_type="{response_type}"}}[{_RATE_INTERVAL}])) '
            f"/ sum(rate(blocky_response_total{{{_JOB}}}[{_RATE_INTERVAL}]))"
        )

    stats = [
        stat(
            "Queries",
            "Queries per second.",
            f"sum(rate(blocky_query_total{{{_JOB}}}[{_RATE_INTERVAL}]))",
            "reqps",
            x=0,
            y=y,
        ),
        stat(
            "Blocked",
            "The share of responses that Blocky blocked.",
            share(_BLOCKED),
            "percentunit",
            x=6,
            y=y,
            decimals=1,
        ),
        stat(
            "Cached",
            "The share of responses that Blocky answered from its cache.",
            share(_CACHED),
            "percentunit",
            x=12,
            y=y,
            decimals=1,
        ),
        stat(
            "Blocking",
            "Whether blocking is enabled. Blocky's API can disable it for a while.",
            f"min(blocky_blocking_enabled{{{_JOB}}})",
            "none",
            x=18,
            y=y,
        ),
        stat(
            "Response time",
            "The 95th percentile of the time Blocky took to answer.",
            _quantile(0.95),
            "s",
            x=0,
            y=y + 4,
        ),
        stat(
            "Errors",
            "Queries per second that Blocky failed to answer, such as when no "
            "upstream server responded.",
            f"sum(rate(blocky_error_total{{{_JOB}}}[{_RATE_INTERVAL}]))",
            "reqps",
            x=6,
            y=y + 4,
            thresholds=[
                {"color": "green", "value": None},
                {"color": "red", "value": 0.001},
            ],
        ),
        stat(
            "Denylist entries",
            "Domains on the denylists that Blocky loaded. Zero means that it failed "
            "to download them, and blocks nothing.",
            f"sum(blocky_denylist_cache_entries{{{_JOB}}})",
            "short",
            x=12,
            y=y + 4,
            decimals=0,
            thresholds=[
                {"color": "red", "value": None},
                {"color": "text", "value": 1},
            ],
        ),
        stat(
            "Metrics",
            "Whether VictoriaMetrics could scrape Blocky's metrics.",
            f"min(up{{{_JOB}}})",
            "none",
            x=18,
            y=y + 4,
        ),
    ]
    for panel, statuses in [(stats[3], _BLOCKING_STATUSES), (stats[7], _UP_STATUSES)]:
        panel["fieldConfig"]["defaults"]["mappings"] = value_mappings(statuses)["value"]
    return stats


def _quantile(q: float) -> str:
    return (
        f"histogram_quantile({q}, sum by (le) (rate("
        f"blocky_request_duration_seconds_bucket{{{_JOB}}}[{_RATE_INTERVAL}])))"
    )


def _responses_by(
    title: str, description: str, label: str, grid_pos: dict[str, int]
) -> dict[str, Any]:
    return timeseries(
        title,
        description,
        [
            target(
                f"sum by ({label}) (rate(blocky_response_total{{{_JOB}}}"
                f"[{_RATE_INTERVAL}]))",
                legend=legend_var(label),
            )
        ],
        grid_pos,
        "reqps",
    )


def _response_times(grid_pos: dict[str, int]) -> dict[str, Any]:
    quantiles = [(0.5, "A"), (0.95, "B"), (0.99, "C")]
    return timeseries(
        "Response time",
        "Percentiles of the time Blocky took to answer. Blocky measures it in "
        "buckets, so the percentiles are estimates.",
        [
            target(_quantile(q), legend=f"p{round(q * 100)}", ref_id=r)
            for q, r in quantiles
        ],
        grid_pos,
        "s",
        stacked=False,
        fill_opacity=0,
    )


def _filter_link(variable: str, other: str) -> dict[str, Any]:
    """
    Returns a data link that reloads the dashboard with variable matching exactly the
    clicked value, and keeps the other variable and the time range.
    """
    return {
        "id": "links",
        "value": [
            {
                "title": f"Show only this {variable}'s lookups",
                "url": (
                    f"/d/{UID}?${{__url_time_range}}&${{{other}:queryparam}}"
                    f"&var-{variable}=%5E${{__value.raw:percentencode}}%24"
                ),
            }
        ],
    }


def _top_domains(
    title: str, description: str, query: str, grid_pos: dict[str, int]
) -> dict[str, Any]:
    return logs_table(
        title,
        description,
        f"{query} | stats by ({_DOMAIN}) count() as lookups, "
        f"count_uniq({_CLIENT}) as clients "
        f"| sort by (lookups desc) | limit {_TOP}",
        {_DOMAIN: "Domain", "lookups": "Lookups", "clients": "Clients"},
        ["lookups", "clients"],
        grid_pos,
        [column("Domain", [_filter_link("domain", "client")])],
        sort_by="Lookups",
    )


def _top_clients(query: str, grid_pos: dict[str, int]) -> dict[str, Any]:
    return logs_table(
        "Top clients",
        "The clients that looked up the selected domains most often, how many of "
        "their lookups were blocked, and how many domains they looked up. Click a "
        "client to show only its lookups.",
        f"{query} | stats by ({_CLIENT}) count() as lookups, "
        f"count() if ({_RESPONSE_TYPE}:={_BLOCKED}) as blocked, "
        f"count_uniq({_DOMAIN}) as domains "
        f"| sort by (lookups desc) | limit {_TOP}",
        {
            _CLIENT: "Client",
            "lookups": "Lookups",
            "blocked": "Blocked",
            "domains": "Domains",
        },
        ["lookups", "blocked", "domains"],
        grid_pos,
        [column("Client", [_filter_link("client", "domain")])],
        sort_by="Lookups",
    )


def _lookups_by(
    title: str,
    description: str,
    query: str,
    field: str,
    grid_pos: dict[str, int],
) -> dict[str, Any]:
    return timeseries(
        title,
        description,
        [
            logs_target(
                f"{query} | stats by ({field}) count() as lookups",
                "statsRange",
                legend=legend_var(field),
            )
        ],
        grid_pos,
        "short",
        datasource=LOGS_DATASOURCE,
    )
