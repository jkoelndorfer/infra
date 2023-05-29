"""
lib/facts
---------

This module contains custom pyinfra fact definitions.
"""

from pyinfra.facts.server import LsbRelease


class DistroId(LsbRelease):
    @staticmethod
    def process(output) -> str:
        lsb_release = LsbRelease.process(output)

        return lsb_release["id"]
