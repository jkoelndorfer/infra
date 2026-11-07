"""
projects.homelab.monitoring.blocky_metrics
==========================================

This module defines how VictoriaMetrics scrapes Blocky's Prometheus metrics [1],
which homelab.blocky serves.

Blocky counts queries by client and record type, and responses by how it answered
them: resolved upstream, from its cache, or blocked, among others. It also reports
how long it took to answer, the size of its cache and denylists, and whether
blocking is enabled.

The metrics are not authenticated. homelab.blocky admits only VictoriaMetrics to
them.

[1]: https://0xerr0r.github.io/blocky/latest/prometheus_grafana/
"""

from infralib import DeploymentContext

from ..blocky import HomelabBlockyProject
from .victoriametrics import ScrapeJob

JOB_NAME = "blocky"


def blocky_scrape_job(dctx: DeploymentContext) -> ScrapeJob:
    """
    Returns the scrape job of Blocky's metrics.
    """
    endpoint = HomelabBlockyProject.metrics_endpoint(dctx)
    return ScrapeJob(
        name=JOB_NAME,
        targets=[endpoint.target],
        metrics_path=endpoint.path,
    )
