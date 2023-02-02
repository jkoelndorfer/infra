"""
lib/data
--------

This module contains code for working with data stored in the
data/ directory under the root of pyinfra.
"""

from os import path
import re
from typing import Mapping

import yaml

_pyinfra_root = path.abspath(
    path.join(path.dirname(__file__), "..")
)
_pyinfra_data_root = path.join(_pyinfra_root, "data")


def load_data(data_path: str, strip_comments: bool) -> str:
    """
    Loads data from a file in $PYINFRA_ROOT/data and returns it
    as a string.
    """
    comment_re = re.compile(r"^\s*#")
    with open(path.join(_pyinfra_data_root, data_path), "r") as f:
        return "\n".join(l for l in f.readlines() if not strip_comments or not comment_re.match(l))


def load_yaml_data(data_path: str) -> Mapping:
    """
    Loads data from a file in $PYINFRA_ROOT/data, parses it as
    YAML, and returns the resulting object.
    """
    return yaml.safe_load(load_data(data_path, strip_comments=False))
