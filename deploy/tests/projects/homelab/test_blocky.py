"""
tests/projects/homelab/test_blocky -- Blocky Project Tests
==========================================================

This module contains tests for the homelab.blocky project.
"""

from ipaddress import IPv4Network

import yaml

from infralib import DeploymentTarget, Environment
from infralib.testing import dummy_infrastructure_configuration, render
from projects.homelab.blocky.project import HomelabBlockyProject


def test_upstream_dns_is_the_routers_address_on_infra() -> None:
    config = dummy_infrastructure_configuration()
    config.homelab.network.networks.infra.ipv4_network = IPv4Network("10.99.0.0/24")

    rendering = render(
        HomelabBlockyProject, DeploymentTarget(Environment.PROD, None), config
    )

    config_map = rendering.one("kubernetes:core/v1:ConfigMap", "config")
    blocky_config = yaml.safe_load(config_map.inputs["data"]["main.yml"])
    assert blocky_config["upstreams"]["groups"]["default"] == ["10.99.0.1"]
