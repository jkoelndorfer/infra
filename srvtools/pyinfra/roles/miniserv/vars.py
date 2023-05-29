"""
roles/miniserv/vars
-------------------

This module contains variables for the miniserv role.
"""

from os import path

data_dir = "/srv/data/0"
files_dir = path.join(path.dirname(__file__), "files")

aqgo_s3_uri = "s3://310987624463-infra-prod/deploy/aqgo/453f327f683b3bf39fc234d310b7335383be92e6/aqgo"
aqgo_sha256sum = "1f796478001096c0a46cacd499e6293f7a829ce2886d9d5b99358ba2ba67e1d9"

rclone_deb_sha256sum = "7c5982b75e7804e6750ddad6dfd74888cf154d1df3377a2aa350a5b7c27e0e1e"
rclone_deb_url = "https://github.com/rclone/rclone/releases/download/v1.61.1/rclone-v1.61.1-linux-arm-v7.deb"

# Time that Syncthing rclone backups run, in "%H:%M" format.
syncthing_backup_time = "04:00"

# Time that Vaultwarden backups (copy to Syncthing) run, in "%H:%M" format.
vaultwarden_backup_time = "23:00"
