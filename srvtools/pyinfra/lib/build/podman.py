"""
lib/build/podman
----------------

This module contains build-time podman code.
"""

from os import path
from shlex import quote as shell_quote
from typing import List

from pyinfra import host
from pyinfra.facts.server import Arch
from pyinfra.operations import files, server

from .. import vars
from ..model.container import Container
from .packages import install_package_set, stage_package_signing_gpg_key


# Output of `gpg --show-keys $key_path` for Kubic release key:
#
# pub   rsa2048 2018-08-03 [SC] [expires: 2025-02-14]
#       2472D6D0D2F66AF87ABA8DA34D64390375060AA4
# uid                      devel:kubic OBS Project <devel:kubic@build.opensuse.org>
kubic_release_key_url = "https://download.opensuse.org/repositories/devel:kubic:libcontainers:unstable/Debian_Testing/Release.key"
kubic_release_key_sha256 = "01ab26439324cb058f4214370535297989b28f743efcfa2b93bb780f2e2aa22d"


def install_podman():
    # The version of podman included with Debian 11 is 3.x,
    # and it does not include the netavark backend for networking.
    #
    # The original network backend, CNI, has a number of shortcomings.
    # Container DNS resolution does not work properly when containers
    # are part of multiple networks, for example.
    #
    # TODO: Remove this once we switch to Debian 12.
    kubic_gpg_key_path, _  = stage_package_signing_gpg_key("kubic", kubic_release_key_url, kubic_release_key_sha256)
    files.template(
        name="[podman] configure kubic apt repo",
        src=path.join(vars.podman_files_dir, "kubic-debian-unstable.list.j2"),
        dest=path.join(vars.apt_sources_list_d, "kubic-debian-unstable.list"),
        owner="root",
        group="root",
        mode="0444",
        _sudo=True,
        dpkg_architecture=host.get_fact(Arch),
        kubic_gpg_key_path=kubic_gpg_key_path,
    )  # pyright: ignore
    return install_package_set("podman")


def pull_ctr_images(ctrs: List[Container]):
    for c in ctrs:
        ctr_image_quoted = shell_quote(c.image)
        server.shell(
            name=f"[podman] container image pull: {c.name}",
            commands=[f"podman pull {ctr_image_quoted}"]
        ) # pyright: ignore


def setup_podman(ctrs: List[Container]):
    """
    Performs all podman build-time setup.
    """
    install_podman()
    pull_ctr_images(ctrs)
