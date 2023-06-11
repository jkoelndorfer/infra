"""
lib/error
---------

Contains definitions for exceptions that are commonly thrown.
"""


class ProvisioningError(Exception):
    """
    Base class for all errors encountered during pyinfra build
    and provision operations.
    """


class UnsupportedLinuxDistribution(ProvisioningError):
    """
    The provisioning operation failed because the current Linux
    distribution is unsupported.
    """

    def __init__(self, distro_id: str) -> None:
        super().__init__(f"Unsupported Linux distribution: {distro_id}")
        self.distro_id = distro_id
