"""
infralib/config/parser -- Infrastructure Configuration Parser
=============================================================

This file defines an infrastructure configuration parser.
"""

from os import PathLike

from .aws import AWSOrganization
from .config import InfrastructureConfiguration
from .domain import Domain
from .gcp import GCPOrganization
from .homelab import Homelab
from .notification import NotificationChannel

from yaml import safe_load as yaml_safe_load


class InfrastructureConfigurationYAMLParser:
    def parse(
        self, path: PathLike[str] | PathLike[bytes]
    ) -> InfrastructureConfiguration:
        with open(path, "r") as f:
            raw_config = yaml_safe_load(f)

        domains = {d["id"]: Domain.from_dict(d) for d in raw_config["domains"]}
        aws_organization = AWSOrganization.from_dict(raw_config["aws_organization"])
        gcp_organization = GCPOrganization.from_dict(raw_config["gcp_organization"])
        homelab = Homelab.from_dict(raw_config["homelab"])
        notification_channels = [
            NotificationChannel.from_dict(d)
            for d in raw_config["notification_channels"]
        ]

        return InfrastructureConfiguration(
            domains,
            aws_organization,
            gcp_organization,
            homelab,
            notification_channels,
        )
