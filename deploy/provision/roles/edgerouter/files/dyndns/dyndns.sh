#!/bin/bash

#############
# dyndns.sh #
#############
#
# dyndns.sh updates a dynamic DNS record with the router's public IP address when
# the record's current value differs.

set -o pipefail

script_path=$(readlink -f "$0")
script_dir=$(dirname "$script_path")

# cfg should be a shell script that sets these variables:
#
# iface: the name of the interface that has the router's public IP, e.g. 'pppoe0'
# hostname: the dns record to update with the router's public IP
# name_server: a name server that is authoritative for hostname
# username: the username used to authenticate with the dyndns service
# password: the password used to authenticate with the dyndns service
# url: the URL of the dyndns HTTP endpoint without query parameters, e.g.
#      'https://example.com/dyndns'
source "${script_dir}/cfg"

# Prints the A record of a name, as served by a specific name server. Prints
# nothing if the record does not exist. Fails if the name server cannot answer.
function lookup_a() {
	local name=$1
	local server=$2
	local output

	# host exits non-zero both when the name does not exist and when the lookup
	# fails. Only the latter is an error: the record does not exist until the
	# first update.
	if ! output=$(host -W 5 -t A "$name" "$server" 2>&1); then
		if [[ "$output" != *NXDOMAIN* ]]; then
			echo "$output" >&2
			return 1
		fi
	fi

	awk '/has address/ { print $4; exit }' <<<"$output"
}

iface_ip=$(ip -o -4 addr show dev "$iface" | awk '{ print $4 }' | cut -d / -f 1 | head -n 1)
if [[ -z "$iface_ip" ]]; then
	echo "Failed getting IP for interface $iface" >&2
	exit 10
fi

if ! dns_ip=$(lookup_a "$hostname" "$name_server"); then
	echo "Failed looking up $hostname at $name_server" >&2
	exit 11
fi

if [[ "$iface_ip" == "$dns_ip" ]]; then
	exit 0
fi

echo "Updating $hostname from '${dns_ip}' to $iface_ip" >&2

# The credentials are passed on standard input, so that they do not appear in the
# process list.
printf 'user = "%s:%s"\n' "$username" "$password" | curl \
	--config - \
	--silent \
	--show-error \
	--fail \
	--max-time 30 \
	--get \
	--data-urlencode "hostname=${hostname}" \
	--data-urlencode "myip=${iface_ip}" \
	"$url"
