"""
lib/model/container
-------------------

This module contains container object models.
"""

from typing import Callable, List, Mapping, Optional


class Volume:
    def __init__(self, src: str, dest: str, mode: str = "rw") -> None:
        self.src = src
        self.dest = dest
        self.mode = mode


class Container:
    def __init__(
        self,
        name: str,
        image: str,
        get_environment: Callable[["Container"], Mapping[str, str]],
        volumes: List[Volume],
        networks: List[str],
        ports: List[str],
        uid: Optional[int],
        gid: Optional[int],
        restart: str,
        max_restarts: int,
        restart_sec: int,
    ) -> None:
        self.name = name
        self.image = image

        # Not all of the container's environment variables can be known at
        # build time, because the environment may contain secrets and we
        # don't want those persisted.
        #
        # Rather than specify the environment directly, the user should pass
        # a function that, when called at provision time, will return the
        # environment variables for the container.
        self.get_environment = get_environment

        self.volumes = volumes
        self.networks = networks
        self.restart = restart
        self.ports = ports

        # For "linuxserver" containers, uid/gid will be implicitly passed
        # via the environment as "PUID" and "PGID".
        self.uid = uid
        self.gid = gid

        # These fields only apply to containers managed by systemd.
        # This could be modeled a little better, but we're only using
        # podman to run containers so the extra complexity doesn't
        # seem worth it.
        self.max_restarts = max_restarts
        self.restart_sec = restart_sec
