"""
roles/edgerouter/secrets
------------------------

This module contains code to load secrets for the edgerouter role.
"""

import json
import os
import subprocess

from typing import Dict

import yaml

from .model import (
    CenturyLink,
    DNS,
    DynDNSConfig,
    Host,
    PortForward,
    StaticDHCP,
    StaticDHCPs,
    User,
    WireguardPeer,
    WireguardPeers,
)

# TODO: Clean this up.


def _bw_cmd(*args):
    return ["bw", "--nointeraction", "--raw", *args]


def _sync_bw():
    subprocess.run(_bw_cmd("sync"), capture_output=True)


def _find_router_secrets_item():
    list_proc = subprocess.run(_bw_cmd("list", "items"), capture_output=True)
    if list_proc.returncode != 0:
        raise Exception("failed listing Bitwarden items")
    bw_items = json.loads(list_proc.stdout)
    for i in bw_items:
        for f in i.get("fields", []):
            # Bitwarden boolean fields are still strings :-/
            if f.get("name", None) == "Router Secrets" and f.get("value", "false") == "true":
                return i
    raise Exception("failed to find Bitwarden item with 'Router Secrets' set")


def _get_most_recent_router_secrets(item):
    secrets_attachment = sorted(item["attachments"], key=lambda i: i["fileName"], reverse=True)[0]
    attachment_filename = secrets_attachment["fileName"]
    get_proc = subprocess.run(
        _bw_cmd("get", "attachment", attachment_filename, "--itemid", item["id"]),
        capture_output=True,
    )
    if get_proc.returncode != 0:
        raise Exception(f"failed getting bitwarden attachment {attachment_filename}")
    attachment_content = get_proc.stdout.decode("utf-8")
    return yaml.safe_load(attachment_content)


# In the previous Ansible configuration, many router secrets were retrieved
# from AWS SSM Parameter Store. This worked okay, as long as the router
# was properly configured and internet access was working. However,
# if you were doing a fresh provision, internet was down, or the current
# router config was botched, that model suddenly did not work so well.
#
# Instead, we provide a YAML-formatted file that contains the secrets.
# This works entirely offline in a greenfield setup. Additionally,
# for regular maintenance we can fetch the secrets automatically from
# Bitwarden.
_s = dict()
_f_env = "EDGEROUTER_SECRETS_FILE"
edgerouter_secrets_file = os.environ.get(_f_env, None)
if edgerouter_secrets_file is not None:
    # EDGEROUTER_SECRETS_FILE is specified in the environment; try to load
    # secrets from the provided path.
    try:
        with open(os.environ[_f_env]) as f:
            _s = yaml.safe_load(f)
    except Exception:
        raise Exception(f"failed reading secrets from edgerouter secrets file at {edgerouter_secrets_file}")
elif os.environ.get("BW_SESSION", None) is not None:
    # No EDGEROUTER_SECRETS_FILE was specified, but we do have an active
    # Bitwarden session. Try to read secrets from Bitwarden.
    _sync_bw()
    _secrets_item = _find_router_secrets_item()
    _s = _get_most_recent_router_secrets(_secrets_item)
else:
    raise Exception(
        "failed loading secrets; neither EDGEROUTER_SECRETS_FILE nor BW_SESSION are specified (try `bw unlock`)"
    )

_a = _s["admin"]
admin = User(_a["username"], _a["full_name"], _a["password"], _a["hash_salt"], _a["pubkey"])
centurylink = CenturyLink.from_dict(_s["centurylink"])
dyndns = DynDNSConfig.from_dict(_s["dyndns"])
dns = [DNS.from_dict(name, d) for name, d in _s["dns"].items()]
hosts: Dict[str, Host] = dict()
kserv_static_dhcp = StaticDHCPs(StaticDHCP.from_dict(name, d) for name, d in _s["kserv_static_dhcp"].items())
port_forwards = [PortForward.from_dict(d) for d in _s["port_forwards"]]
static_dhcp = StaticDHCPs(StaticDHCP.from_dict(name, d) for name, d in _s["static_dhcp"].items())
wireguard_key = _s["wireguard_key"]
wireguard_peers = WireguardPeers([WireguardPeer.from_dict(name, d) for name, d in _s["wireguard_peers"].items()])

for _i in dns:
    hosts[_i.name] = Host.from_dns(_i)

for _j in static_dhcp:
    hosts[_j.name] = Host.from_static_dhcp(_j)
