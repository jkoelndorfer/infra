"""
roles/miniserv/vars
-------------------

This module contains variables for the miniserv role.
"""

from os import path

data_dir = "/srv/data/0"
files_dir = path.join(path.dirname(__file__), "files")

# Time that Vaultwarden backups run, in "%H:%M" format.
vaultwarden_backup_time = "23:00"
