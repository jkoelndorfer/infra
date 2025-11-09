"""
backup.restic.error
====================

Contains Restic-related error classes.
"""

from .model import ResticResult


class ResticError(Exception):
    """
    Superclass for all restic-related errors.
    """

    def __init__(self, msg: str, result: ResticResult) -> None:
        super().__init__(msg)
        self.result = result


class InvalidResticRepositoryPasswordError(ResticError):
    """
    Exception that is raised when the password for the Restic repository is invalid.
    """
