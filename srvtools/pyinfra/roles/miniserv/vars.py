"""
roles/miniserv/vars
-------------------

This module contains variables for the miniserv role.
"""

from os import path

data_dir = "/srv/data/0"
files_dir = path.join(path.dirname(__file__), "files")

rclone_deb_sha256sum = "7c5982b75e7804e6750ddad6dfd74888cf154d1df3377a2aa350a5b7c27e0e1e"
rclone_deb_url = "https://github.com/rclone/rclone/releases/download/v1.61.1/rclone-v1.61.1-linux-arm-v7.deb"

# Time that Syncthing rclone backups run, in "%H:%M" format.
syncthing_backup_time = "04:00"

# Time that Vaultwarden backups (copy to Syncthing) run, in "%H:%M" format.
vaultwarden_backup_time = "23:00"
