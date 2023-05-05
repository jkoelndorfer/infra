"""
lib/operations
--------------

Contains custom pyinfra operations.
"""

from typing import Optional

from pyinfra.api import operation


@operation
def download_gpg_key(
    name: str,
    src: str,
    dest: str,
    user: str = "root",
    group: str = "root",
    mode: str = "0444",
    sha256sum: Optional[str] = None,
):
    """
    Download a GPG key from the given `url`, with the given `sha256sum`, and ensures
    that the "dearmored" version is present at `dest`.

    + src: source URL of the GPG key to download
    + dest: where to persist the dearmored version of the key
    + user: user to own the key
    + group: group to own the key
    + mode: permission of the key
    + sha256sum: sha256 digest of the downloaded (not dearmored) key
    """
    gpg_download_staging_dir = ""
