"""
projects.homelab.monitoring.dashboards.host
===========================================

This module defines a Grafana dashboard of the Kubernetes host: its CPU, memory,
hardware temperatures, filesystems, disk I/O and network, the state of its software RAID arrays, and the
health of its disks. The metrics come from the node and smartctl exporters, through
the jobs that `projects.homelab.monitoring.node_exporter` and
`projects.homelab.monitoring.smartctl_exporter` define.
"""

from typing import Any

from infralib import DeploymentContext

from ..node_exporter import HOST_NAME
from ..node_exporter import JOB_NAME as NODE_JOB
from ..smartctl_exporter import JOB_NAME as SMARTCTL_JOB
from .common import (
    Dashboard,
    color_text,
    column,
    fixed_color,
    legend_var,
    legend_vars,
    row,
    stat,
    table,
    target,
    timeseries,
    value_mappings,
)

UID = "homelab-host"

_RATE_INTERVAL = "$__rate_interval"

_NODE = f'job="{NODE_JOB}"'
_SMART = f'job="{SMARTCTL_JOB}"'

# Memory-backed filesystems hold nothing that outlives a reboot.
_FILESYSTEMS = f'{_NODE},fstype!~"tmpfs|ramfs"'

# The node exporter's md state metric has one series per state, with the value 1
# for the array's current state [1]. Each is given a code, so that a table can show
# the state as one value. An array in a state that has no series, such as reshaping,
# gets 0.
#
# [1]: https://github.com/prometheus/node_exporter/blob/v1.12.1/collector/mdadm_linux.go
_MD_STATES = {
    0: ("other", "orange"),
    1: ("active", "green"),
    2: ("check", "blue"),
    3: ("resync", "orange"),
    4: ("recovering", "orange"),
    5: ("inactive", "red"),
}

_SMART_STATUSES = {
    0: ("failed", "red"),
    1: ("passed", "green"),
}

# Raw values of the ATA attributes that count sectors a disk has had trouble with.
# Any above zero is an early sign of failure.
_ATA_SECTOR_ATTRIBUTES = {
    "Reallocated": "Reallocated_Sector_Ct",
    "Pending": "Current_Pending_Sector",
    "Uncorrectable": "Offline_Uncorrectable",
}

_BUSY: list[dict[str, Any]] = [
    {"color": "green", "value": None},
    {"color": "orange", "value": 0.75},
    {"color": "red", "value": 0.9},
]

_ANY_IS_BAD: list[dict[str, Any]] = [
    {"color": "green", "value": None},
    {"color": "red", "value": 1},
]


def host_dashboard(dctx: DeploymentContext) -> Dashboard:
    """
    Returns the host dashboard.
    """
    panels = [
        row("Overview", y=0),
        *_overview_stats(y=1),
        *_health_stats(y=5),
        row("CPU and memory", y=9),
        _cpu({"h": 8, "w": 12, "x": 0, "y": 10}),
        _memory({"h": 8, "w": 12, "x": 12, "y": 10}),
        timeseries(
            "Load average",
            "The host's load averages, and its number of CPUs for comparison.",
            [
                *[
                    target(f"node_load{m}{{{_NODE}}}", legend=f"{m}m", ref_id=r)
                    for m, r in [("1", "A"), ("5", "B"), ("15", "C")]
                ],
                target(_cpu_count(), legend="CPUs", ref_id="D"),
            ],
            {"h": 8, "w": 12, "x": 0, "y": 18},
            "short",
            overrides=[
                column("CPUs", [{"id": "color", "value": fixed_color("red")}]),
            ],
            stacked=False,
            fill_opacity=0,
        ),
        _pressure({"h": 8, "w": 12, "x": 12, "y": 18}),
        _hardware_temperatures({"h": 8, "w": 24, "x": 0, "y": 26}),
        row("Storage", y=34),
        timeseries(
            "Filesystem usage",
            "The share of each filesystem in use.",
            [
                target(
                    f"1 - node_filesystem_avail_bytes{{{_FILESYSTEMS}}} "
                    f"/ node_filesystem_size_bytes{{{_FILESYSTEMS}}}",
                    legend=legend_var("mountpoint"),
                )
            ],
            {"h": 8, "w": 12, "x": 0, "y": 35},
            "percentunit",
            stacked=False,
            fill_opacity=0,
        ),
        timeseries(
            "Disk utilization",
            "The share of time each disk spent busy with I/O.",
            [
                target(
                    _rate("node_disk_io_time_seconds_total", _NODE),
                    legend=legend_var("device"),
                )
            ],
            {"h": 8, "w": 12, "x": 12, "y": 35},
            "percentunit",
            stacked=False,
            fill_opacity=0,
        ),
        _disk_io(
            "Disk throughput",
            "Bytes per second read from and written to each disk.",
            "node_disk_read_bytes_total",
            "node_disk_written_bytes_total",
            "Bps",
            {"h": 8, "w": 12, "x": 0, "y": 43},
        ),
        _disk_latency({"h": 8, "w": 12, "x": 12, "y": 43}),
        row("RAID", y=51),
        _raid_table(y=52),
        timeseries(
            "Array sync progress",
            "How far each array is through a resync, recovery or check. Arrays that "
            "are not syncing show 100%.",
            [
                target(
                    f"node_md_blocks_synced{{{_NODE}}} / node_md_blocks{{{_NODE}}}",
                    legend=legend_var("device"),
                )
            ],
            {"h": 8, "w": 24, "x": 0, "y": 58},
            "percentunit",
            stacked=False,
            fill_opacity=0,
        ),
        row("Disk health", y=66),
        _smart_table(y=67),
        timeseries(
            "Disk temperature",
            "Each disk's temperature, as it reports it.",
            [
                target(
                    f'smartctl_device_temperature{{{_SMART},temperature_type="current"}}',
                    legend=legend_var("device"),
                )
            ],
            {"h": 8, "w": 24, "x": 0, "y": 75},
            "celsius",
            stacked=False,
            fill_opacity=0,
        ),
        row("Network", y=83),
        _network_traffic(
            "Receive",
            "node_network_receive_bytes_total",
            {"h": 8, "w": 12, "x": 0, "y": 84},
        ),
        _network_traffic(
            "Transmit",
            "node_network_transmit_bytes_total",
            {"h": 8, "w": 12, "x": 12, "y": 84},
        ),
        _network_problems({"h": 8, "w": 24, "x": 0, "y": 92}),
    ]
    for i, panel in enumerate(panels, start=1):
        panel["id"] = i

    return {
        "uid": UID,
        "title": "Host",
        "description": (
            f"Resources, storage, RAID arrays, disk health and network of the "
            f"Kubernetes host, {HOST_NAME}."
        ),
        "tags": ["host", "node-exporter", "smartctl"],
        "editable": True,
        "graphTooltip": 1,
        "schemaVersion": 39,
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "1m",
        "timezone": "browser",
        "templating": {"list": []},
        "annotations": {"list": []},
        "links": [],
        "panels": panels,
    }


def _rate(metric: str, selector: str) -> str:
    return f"rate({metric}{{{selector}}}[{_RATE_INTERVAL}])"


def _cpu_count() -> str:
    return f'count(node_cpu_seconds_total{{{_NODE},mode="idle"}})'


def _cpu_busy() -> str:
    """
    Returns the share of CPU time spent busy. Time waiting on I/O is idle time, as
    the CPU could have run something else.
    """
    idle_selector = f'{_NODE},mode=~"idle|iowait"'
    idle = f"sum({_rate('node_cpu_seconds_total', idle_selector)})"
    return f"1 - {idle} / sum({_rate('node_cpu_seconds_total', _NODE)})"


def _overview_stats(y: int) -> list[dict[str, Any]]:
    return [
        stat(
            "Uptime",
            "How long the host has been running since it booted.",
            f"time() - node_boot_time_seconds{{{_NODE}}}",
            "s",
            x=0,
            y=y,
        ),
        stat(
            "CPU",
            "The share of the host's CPU time spent busy.",
            _cpu_busy(),
            "percentunit",
            x=6,
            y=y,
            thresholds=_BUSY,
        ),
        stat(
            "Memory",
            "The share of the host's memory in use, leaving out what the kernel can "
            "reclaim, such as caches.",
            f"1 - node_memory_MemAvailable_bytes{{{_NODE}}} "
            f"/ node_memory_MemTotal_bytes{{{_NODE}}}",
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
            "Load per CPU",
            "The 5 minute load average, divided by the number of CPUs. Above 1, "
            "tasks are waiting for a CPU.",
            f"node_load5{{{_NODE}}} / scalar({_cpu_count()})",
            "short",
            x=18,
            y=y,
            decimals=2,
            thresholds=[
                {"color": "green", "value": None},
                {"color": "orange", "value": 1},
                {"color": "red", "value": 2},
            ],
        ),
    ]


def _health_stats(y: int) -> list[dict[str, Any]]:
    return [
        stat(
            "Missing RAID members",
            "The number of disks the RAID arrays are missing, out of the number "
            "they need. Above zero, an array is degraded.",
            f"sum(node_md_disks_required{{{_NODE}}} "
            f'- ignoring (state) node_md_disks{{{_NODE},state="active"}})',
            "short",
            x=0,
            y=y,
            decimals=0,
            thresholds=_ANY_IS_BAD,
        ),
        stat(
            "Failed RAID members",
            "The number of disks that the RAID arrays have marked failed.",
            f'sum(node_md_disks{{{_NODE},state="failed"}})',
            "short",
            x=6,
            y=y,
            decimals=0,
            thresholds=_ANY_IS_BAD,
        ),
        stat(
            "Disks failing SMART",
            "The number of disks whose SMART self-assessment reports failure.",
            f"sum(1 - smartctl_device_smart_status{{{_SMART}}})",
            "short",
            x=12,
            y=y,
            decimals=0,
            thresholds=_ANY_IS_BAD,
        ),
        stat(
            "Hottest disk",
            "The temperature of the hottest disk.",
            f'max(smartctl_device_temperature{{{_SMART},temperature_type="current"}})',
            "celsius",
            x=18,
            y=y,
            thresholds=[
                {"color": "green", "value": None},
                {"color": "orange", "value": 50},
                {"color": "red", "value": 60},
            ],
        ),
    ]


def _cpu(grid_pos: dict[str, int]) -> dict[str, Any]:
    total = f"scalar(sum({_rate('node_cpu_seconds_total', _NODE)}))"
    busy = _rate("node_cpu_seconds_total", f'{_NODE},mode!="idle"')
    return timeseries(
        "CPU",
        "The share of the host's CPU time spent in each mode, other than idle.",
        [target(f"sum by (mode) ({busy}) / {total}", legend=legend_var("mode"))],
        grid_pos,
        "percentunit",
    )


def _memory(grid_pos: dict[str, int]) -> dict[str, Any]:
    def mem(field: str) -> str:
        return f"node_memory_{field}_bytes{{{_NODE}}}"

    cached = f"{mem('Cached')} + {mem('SReclaimable')}"
    parts = {
        "used": f"{mem('MemTotal')} - {mem('MemFree')} - {mem('Buffers')} - {cached}",
        "buffers": mem("Buffers"),
        "cached": cached,
        "free": mem("MemFree"),
    }
    return timeseries(
        "Memory",
        "The host's memory, by use. The kernel frees buffers and caches as needed.",
        [
            target(expr, legend=name, ref_id=ref_id)
            for (name, expr), ref_id in zip(parts.items(), "ABCD")
        ],
        grid_pos,
        "bytes",
        overrides=[
            column("free", [{"id": "color", "value": fixed_color("green")}]),
        ],
    )


def _pressure(grid_pos: dict[str, int]) -> dict[str, Any]:
    resources = {"CPU": "cpu", "memory": "memory", "I/O": "io"}
    return timeseries(
        "Pressure",
        "The share of time that some task waited for each resource [1]. Sustained "
        "pressure means that resource is a bottleneck.\n\n"
        "[1]: https://docs.kernel.org/accounting/psi.html",
        [
            target(
                _rate(f"node_pressure_{resource}_waiting_seconds_total", _NODE),
                legend=name,
                ref_id=ref_id,
            )
            for (name, resource), ref_id in zip(resources.items(), "ABC")
        ],
        grid_pos,
        "percentunit",
        stacked=False,
        fill_opacity=0,
    )


def _hardware_temperatures(grid_pos: dict[str, int]) -> dict[str, Any]:
    """
    Returns a graph of every temperature sensor that the kernel's hardware
    monitoring drivers [1] expose, such as the CPU's, the chipset's and the
    memory's. Which there are depends on the hardware.

    Each series is named by its chip, such as coretemp or k10temp, its sensor, and
    the sensor's label, where the driver gives one.

    [1]: https://docs.kernel.org/hwmon/sysfs-interface.html
    """
    sensor = ("instance", "chip", "sensor")
    on_sensor = f"on ({', '.join(sensor)})"
    temps = f"node_hwmon_temp_celsius{{{_NODE}}}"
    # The chip's name and the sensor's label are series of their own, with the
    # value 1. A sensor that either is missing for is kept without it.
    named = (
        f"({temps} * on (instance, chip) group_left (chip_name) "
        f"node_hwmon_chip_names{{{_NODE}}}) or {on_sensor} {temps}"
    )
    labeled = (
        f"(({named}) * {on_sensor} group_left (label) "
        f"node_hwmon_sensor_label{{{_NODE}}}) or {on_sensor} ({named})"
    )
    return timeseries(
        "Hardware temperatures",
        "The temperature of each hardware sensor on the host. CPU sensors usually "
        "come from the coretemp (Intel) or k10temp (AMD) chip.",
        [target(labeled, legend=legend_vars("chip_name", "sensor", "label"))],
        grid_pos,
        "celsius",
        stacked=False,
        fill_opacity=0,
    )


def _disk_io(
    title: str,
    description: str,
    read_metric: str,
    write_metric: str,
    unit: str,
    grid_pos: dict[str, int],
) -> dict[str, Any]:
    return timeseries(
        title,
        description,
        [
            target(
                _rate(metric, _NODE),
                legend=f"{legend_var('device')} {direction}",
                ref_id=ref_id,
            )
            for metric, direction, ref_id in [
                (read_metric, "read", "A"),
                (write_metric, "write", "B"),
            ]
        ],
        grid_pos,
        unit,
        stacked=False,
        fill_opacity=10,
    )


def _disk_latency(grid_pos: dict[str, int]) -> dict[str, Any]:
    def latency(direction: str, count_metric: str) -> str:
        time = _rate(f"node_disk_{direction}_time_seconds_total", _NODE)
        return f"{time} / ({_rate(count_metric, _NODE)} > 0)"

    return timeseries(
        "Disk latency",
        "The average time each disk took to complete a read or a write. Only disks "
        "that completed any are shown.",
        [
            target(
                latency("read", "node_disk_reads_completed_total"),
                legend=f"{legend_var('device')} read",
                ref_id="A",
            ),
            target(
                latency("write", "node_disk_writes_completed_total"),
                legend=f"{legend_var('device')} write",
                ref_id="B",
            ),
        ],
        grid_pos,
        "s",
        stacked=False,
        fill_opacity=0,
    )


def _raid_table(y: int) -> dict[str, Any]:
    """
    Returns a table with a row per software RAID array: its state, its disks by
    state, and how far it is through a sync.
    """
    group = "max by (device)"
    state = " + ".join(
        f'{code} * sum by (device) (node_md_state{{{_NODE},state="{name}"}})'
        for code, (name, _) in _MD_STATES.items()
        if code > 0
    )

    def disks(disk_state: str) -> str:
        return f'{group} (node_md_disks{{{_NODE},state="{disk_state}"}})'

    columns = {
        "State": state,
        "Active": disks("active"),
        "Required": f"{group} (node_md_disks_required{{{_NODE}}})",
        "Failed": disks("failed"),
        "Spare": disks("spare"),
        "Synced": (
            f"{group} (node_md_blocks_synced{{{_NODE}}} / node_md_blocks{{{_NODE}}})"
        ),
    }
    counts: list[dict[str, Any]] = [
        {"id": "unit", "value": "short"},
        {"id": "decimals", "value": 0},
    ]
    return table(
        "Arrays",
        "Each array's state and disks. An array is degraded when it has fewer "
        "active disks than it requires.",
        columns,
        {"device": "Array"},
        {"h": 6, "w": 24, "x": 0, "y": y},
        [
            column("State", [value_mappings(_MD_STATES), color_text()]),
            *[column(name, counts) for name in ["Active", "Required", "Spare"]],
            column(
                "Failed",
                [
                    *counts,
                    {
                        "id": "thresholds",
                        "value": {"mode": "absolute", "steps": _ANY_IS_BAD},
                    },
                    {"id": "color", "value": {"mode": "thresholds"}},
                    color_text(),
                ],
            ),
            column("Synced", [{"id": "unit", "value": "percentunit"}]),
        ],
        sort_by="Array",
    )


def _smart_table(y: int) -> dict[str, Any]:
    """
    Returns a table with a row per disk: its model and serial number, its SMART
    status, temperature and power-on time, and its error counters.
    """
    info = f"smartctl_device{{{_SMART}}}"

    def by_disk(expr: str) -> str:
        # Joins the disk's model and serial number from its info series, whose
        # value is 1, so that every column has the same labels.
        return (
            "max by (device, model_name, serial_number) "
            f"(({expr}) * on (instance, device) "
            f"group_left (model_name, serial_number) {info})"
        )

    columns = {
        "SMART": f"smartctl_device_smart_status{{{_SMART}}}",
        "Temperature": (
            f'smartctl_device_temperature{{{_SMART},temperature_type="current"}}'
        ),
        "Powered on": f"smartctl_device_power_on_seconds{{{_SMART}}}",
        **{
            name: (
                f"smartctl_device_attribute{{{_SMART},"
                f'attribute_name="{attribute}",attribute_value_type="raw"}}'
            )
            for name, attribute in _ATA_SECTOR_ATTRIBUTES.items()
        },
        "Media errors": f"smartctl_device_media_errors{{{_SMART}}}",
        "Wear": f"smartctl_device_percentage_used{{{_SMART}}} / 100",
    }
    error_counter: list[dict[str, Any]] = [
        {"id": "unit", "value": "short"},
        {"id": "decimals", "value": 0},
        {
            "id": "thresholds",
            "value": {"mode": "absolute", "steps": _ANY_IS_BAD},
        },
        {"id": "color", "value": {"mode": "thresholds"}},
        color_text(),
    ]
    return table(
        "Disks",
        "Each disk's SMART self-assessment, temperature and power-on time, and the "
        "error counters that warn of failure. Reallocated, pending and "
        "uncorrectable sectors are reported by ATA disks, and media errors and wear "
        "by NVMe disks.",
        {name: by_disk(expr) for name, expr in columns.items()},
        {"device": "Disk", "model_name": "Model", "serial_number": "Serial"},
        {"h": 8, "w": 24, "x": 0, "y": y},
        [
            column("SMART", [value_mappings(_SMART_STATUSES), color_text()]),
            column("Temperature", [{"id": "unit", "value": "celsius"}]),
            column("Powered on", [{"id": "unit", "value": "s"}]),
            *[
                column(name, error_counter)
                for name in [*_ATA_SECTOR_ATTRIBUTES, "Media errors"]
            ],
            column("Wear", [{"id": "unit", "value": "percentunit"}]),
        ],
        sort_by="Disk",
    )


def _network_traffic(
    direction: str, metric: str, grid_pos: dict[str, int]
) -> dict[str, Any]:
    return timeseries(
        direction,
        "Bits per second, by interface.",
        [target(f"{_rate(metric, _NODE)} * 8", legend=legend_var("device"))],
        grid_pos,
        "bps",
        stacked=False,
        fill_opacity=10,
    )


def _network_problems(grid_pos: dict[str, int]) -> dict[str, Any]:
    counters = [
        ("receive_errs", "receive errors"),
        ("transmit_errs", "transmit errors"),
        ("receive_drop", "receive drops"),
        ("transmit_drop", "transmit drops"),
    ]
    return timeseries(
        "Errors and drops",
        "Packets per second that each interface could not receive or send because "
        "of errors, or dropped. Only interfaces with any are shown.",
        [
            target(
                f"{_rate(f'node_network_{counter}_total', _NODE)} > 0",
                legend=f"{legend_var('device')} {name}",
                ref_id=ref_id,
            )
            for (counter, name), ref_id in zip(counters, "ABCD")
        ],
        grid_pos,
        "pps",
        stacked=False,
        fill_opacity=10,
    )
