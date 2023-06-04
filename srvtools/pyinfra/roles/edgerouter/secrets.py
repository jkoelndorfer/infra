"""
roles/edgerouter/secrets
------------------------

This module contains code to load secrets for the edgerouter role.
"""

import os

import yaml

from .model import (
    CenturyLink,
    DNS,
    DynDNSConfig,
    Host,
    PortForward,
    StaticDHCP,
    User,
    WireguardPeer,
    WireguardPeers,
)

# In the previous Ansible configuration, many router secrets were retrieved
# from AWS SSM Parameter Store. This worked okay, as long as the router
# was properly configured and internet access was working. However,
# if you were doing a fresh provision, internet was down, or the current
# router config was botched, that model suddenly did not work so well.
#
# Instead, we provide a YAML-formatted file that contains the secrets.
# This works entirely offline.

f_env = "EDGEROUTER_SECRETS_FILE"
try:
    with open(os.environ[f_env]) as f:
        _s = yaml.safe_load(f)
except KeyError:
    raise Exception(f"missing required environment variable {f_env} pointing at edgerouter secrets document")

_a = _s["admin"]
admin = User(_a["username"], _a["full_name"], _a["password"], _a["hash_salt"], _a["pubkey"])
centurylink = CenturyLink.from_dict(_s["centurylink"])
dyndns = DynDNSConfig.from_dict(_s["dyndns"])
dns = [DNS.from_dict(name, d) for name, d in _s["dns"].items()]
hosts = dict()
port_forwards = [PortForward.from_dict(d) for d in _s["port_forwards"]]
static_dhcp = [StaticDHCP.from_dict(name, d) for name, d in _s["static_dhcp"].items()]
wireguard_peers = WireguardPeers(
    [WireguardPeer.from_dict(name, d) for name, d in _s["wireguard_peers"].items()]
)

for d in dns:
    hosts[d.name] = Host.from_dns(d)

for d in static_dhcp:
    hosts[d.name] = Host.from_static_dhcp(d)
