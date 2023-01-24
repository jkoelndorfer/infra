#!/bin/bash

set -o pipefail

script_dir=$(dirname "$0")
cd "$script_dir"

# cfg should be a shell script that sets these variables:
#
# iface: the name of the interface that has the router's public IP, e.g. 'pppoe0'
# hostname: the dns record to update with the router's public IP
# username: the username used to authenticate with the dyndns service
# password: the password used to authenticate with the dyndns service
# url: the URL of the dyndns HTTP endpoint without query parameters, e.g.
#      'https://example.com/dyndns'
source cfg

iface_ip=$(ip -o a show dev "$iface" | awk '$3 == "inet" { print $4 }' | grep -Eo '^[^/]+')
if [[ -z "$iface_ip" ]]; then
  echo "Failed getting IP for interface $iface" >&2
  exit 10
fi

dns_ip=$(getent hosts "$hostname" | awk '{ print $1 }')

dns_lookup_rc="$?"
if [[ "$dns_lookup_rc" != 0 ]]; then
  echo "Failed looking up $hostname" >&2
  exit 11
fi

if [[ "$iface_ip" == "$dns_ip" ]]; then
  echo "IP for $hostname ($dns_ip) is current; nothing to do" >&2
  exit 0
fi

curl -X POST -u "$username:$password" "$url?hostname=$hostname&myip=$iface_ip"
