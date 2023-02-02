"""
roles/edgerouter/vars
---------------------

This module contains variables for the edgerouter role.
"""

from ipaddress import ip_network
from os import path

config_dir = "/config"
router_runtime_cfg = path.join(config_dir, "config.pyinfra")
router_boot_cfg = path.join(config_dir, "config.boot")
cache_dir = "/var/cache"
user_data_config_dir = path.join(config_dir, "user-data")
post_config_d_dir = path.join(config_dir, "scripts", "post-config.d")

config_user = "root"
config_group = "vyattacfg"

lan_network = ip_network("192.168.192.0/20")

# The router is always the first address in the network.
router_ip = next(lan_network.hosts())
router_ip_cidr = f"{router_ip}/{lan_network.prefixlen}"

modem_network = ip_network("172.17.17.0/24")
router_ip_modem_net = next(modem_network.hosts())
router_ip_modem_net_cidr = f"{router_ip_modem_net}/{modem_network.prefixlen}"

dhcp_start = "192.168.194.10"
dhcp_end = "192.168.194.250"

# Subnet where bad citizens end up. Examples include Roku TVs,
# which ignore DHCP-prescribed DNS.
bad_citizens_subnet = ip_network("192.168.201.0/24")

upstream_dns = [
  "208.67.222.222",
  "208.67.220.220",
]

wan_iface = "pppoe0"

wireguard_deb_url = "https://github.com/WireGuard/wireguard-vyatta-ubnt/releases/download/1.0.20220627-1/e300-v2-v1.0.20220627-v1.0.20210914.deb"  # noqa: E501
wireguard_deb_sha256sum = "4774d0adf24b56c38c1d52eb1e6157a3e18e7c00868ee7301334384d28cc7bee"
wireguard_cache_dir = path.join(cache_dir, "wireguard")
wireguard_key_path = path.join(config_dir, "wireguard", "wg.key")
wireguard_network = ip_network("192.168.222.0/24")
wireguard_router_ip = next(wireguard_network.hosts())
wireguard_router_ip_cidr = f"{wireguard_router_ip}/{wireguard_network.prefixlen}"
wireguard_listen_port = 51820
