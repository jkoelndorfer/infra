"""
backup.log
==========

Contains logging helper code.
"""

import logging
from typing import Optional

LOG_PREFIX = "johnk.infra.backupjob"


def logger(name: Optional[str]) -> logging.Logger:
    """
    Returns a logger in this application's logging namespace.

    If name is None, returns the root logger for this application.
    """
    if name is None:
        log_name = LOG_PREFIX
    else:
        log_name = f"{LOG_PREFIX}.{name}"
    return logging.getLogger(log_name)
