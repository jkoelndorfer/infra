"""
lib/build/packages
------------------

This module contains build-time package management code.
"""

from pyinfra.operations import apt, files, pacman

from ..data import load_package_set
from ..error import UnsupportedLinuxDistribution
from ..vars import distro_id

if distro_id == "Debian":
    package_signing_key_staging_dir = "/etc/apt/trusted.gpg.custom"
elif distro_id == "Arch":
    package_signing_key_staging_dir = "/etc/pacman.d/gnupg.custom"
else:
    raise UnsupportedLinuxDistribution(distro_id)


_package_signing_key_staging_dir_configured = False


def install_package_set(name: str):
    """
    Installs the given package set.
    """
    op_name = f"[packages] install package set {name}"
    package_set = load_package_set(name)

    if distro_id == "Debian":
        apt.packages(
            name=op_name,
            packages=package_set.debian_packages,
            present=True,
            update=True,
            _sudo=True
        )  # pyright: ignore
    elif distro_id == "Arch":
        pacman.packages(
            name=op_name,
            packages=package_set.arch_packages,
            present=True,
            update=True,
            _sudo=True
        )  # pyright: ignore
    else:
        raise UnsupportedLinuxDistribution(distro_id)


def _configure_package_signing_key_staging_dir():
    """
    Creates a directory to store package signing keys that
    are used to validate third-party packages.
    """
    global _package_signing_key_staging_dir_configured
    if _package_signing_key_staging_dir_configured:
        return
    files.directory(
        name="[packages] create package signing key directory",
        path=package_signing_key_staging_dir,
        user="root",
        group="root",
        mode="0755",
        _sudo=True,
    )
    _package_signing_key_staging_dir_configured = True


def stage_package_signing_gpg_key(name: str, url: str, sha256sum: str):
    """
    Stages a package signing key within the package_signing_keys_dir, but
    does not configure the package manager to trust the signing key.

    Assumes that the key at url is in OpenPGP binary format.
    """
    _configure_package_signing_key_staging_dir()
    dest = f"{package_signing_key_staging_dir}/{name}.key"
    op = files.download(
        name=f"[packages] stage package signing key: {name}",
        src=url,
        dest=dest,
        sha256sum=sha256sum,
        _sudo=True,
    )
    return (dest, op)
