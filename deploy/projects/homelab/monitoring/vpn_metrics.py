"""
projects.homelab.monitoring.vpn_metrics
=======================================

This module defines how VictoriaMetrics scrapes wg-easy's Prometheus metrics [1],
which homelab.vpn serves.

wg-easy reports, for each peer, the bytes sent to and received from it and the
seconds since its latest handshake, labeled by the peer's name and address. It also
reports how many peers are configured, enabled and connected. A peer counts as
connected if its latest handshake was less than CONNECTED_HANDSHAKE_SECONDS ago.

[1]: https://wg-easy.github.io/wg-easy/latest/advanced/metrics/prometheus/
"""

from infralib import DeploymentContext

from ..vpn import HomelabVPNProject
from .victoriametrics import ScrapeBearerAuth, ScrapeJob

JOB_NAME = "vpn"

CONNECTED_HANDSHAKE_SECONDS = 600
"""
How recent wg-easy requires a peer's latest handshake to be to count it as connected.
WireGuard renews a session's keys every two minutes while it carries traffic.
"""


def vpn_scrape_job(dctx: DeploymentContext) -> ScrapeJob:
    """
    Returns the scrape job of wg-easy's metrics.
    """
    endpoint = HomelabVPNProject.metrics_endpoint(dctx)
    return ScrapeJob(
        name=JOB_NAME,
        targets=[endpoint.target],
        metrics_path=endpoint.path,
        auth=ScrapeBearerAuth(token=endpoint.token),
    )
