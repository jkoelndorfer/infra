"""
lib/vars
--------

This module contains common variables.
"""

from ipaddress import ip_network
from os import path

files_dir = path.join(path.dirname(__file__), "files")

ctr_env_dir = "/usr/local/etc/ctr-env"
systemd_unit_dir = "/etc/systemd/system"

# Some components other than the router need to know the topography
# of the home network. For example, pihole needs to know what its
# upstream DNS is.
home_lan_network = ip_network("192.168.192.0/20")

# The router is always the first address in the network.
home_router_ip = next(home_lan_network.hosts())
home_router_ip_cidr = f"{home_router_ip}/{home_lan_network.prefixlen}"
