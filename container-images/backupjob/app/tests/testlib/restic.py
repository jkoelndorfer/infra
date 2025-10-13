"""
testlib.restic
==============

Contains helper code for restic tests.
"""

from typing import Callable

ExpectedResticCommand = Callable[[list[str]], list[str]]
