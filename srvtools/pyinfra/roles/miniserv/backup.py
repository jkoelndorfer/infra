"""
roles/miniserv/backup
---------------------

This module contains backup-related variables for the miniserv role.
"""

from lib.aws import ssm_parameter_value

from .containers import photoprism_container, syncthing_container
from .model import Backup

bucket = ssm_parameter_value("/prod/backup/bucket")
limited_bw = "1M:12M"
bw_limit = f"00:00,off 07:00,{ limited_bw }"

backups = [
    Backup(
        container_name="photoprism",
        time="02:00",
        working_directory=photoprism_container.data_dir,
        src="./",
        dest=f"s3:{bucket}/photoprism/rclone/",
    ),
    Backup(
        container_name="syncthing",
        time="04:00",
        working_directory=syncthing_container.data_dir,
        src="data/",
        dest=f"s3:{bucket}/syncthing/rclone/data",
    ),
]
