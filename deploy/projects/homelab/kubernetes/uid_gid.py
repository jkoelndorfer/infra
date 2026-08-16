"""
projects.homelab.kubernetes.uid_gid
===================================

This module defines Kubernetes service UID and GID assignments.
"""

from infralib import Environment


# These are the base UIDs and GIDs for dev and prod.
#
# UIDs and GIDs below are defined as offsets starting
# at these ranges.
_base = {
    Environment.DEV: 100000,
    Environment.PROD: 200000,
    Environment.TEST: 300000,
}

# These are the IDs for each service. As noted above, the IDs
# specified here are *offsets from the base ID*. The base ID
# is dependent upon the environment.
_service_ids = {
    "traefik": 0,
    "ctr_registry": 1,
    "syncthing": 2,
    "backup": 3,
    "vaultwarden": 4,
    "speedtest": 5,
    "unifi": 6,
    "blocky": 7,
}


def uid_gid(env: Environment, service_name: str) -> int:
    """
    Returns the UID/GID assigned to the given service.
    """
    env_base = _base[env]
    service_id = _service_ids[service_name]

    return env_base + service_id
