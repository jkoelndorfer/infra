"""
lib/model/container
-------------------

This module contains container object models.
"""

from ipaddress import IPv4Address, IPv4Network
import os
from typing import Any, Callable, List, Literal, Mapping, Optional

from ..pyinfra import Pyinfra


class ContainerNetwork:
    def __init__(self, name: str, network: IPv4Network) -> None:
        self.name = name
        self.network = network

    @property
    def gateway_address(self) -> IPv4Address:
        # The gateway is the first address in the network, by convention.
        return next(self.network.hosts())

    @property
    def systemd_service_name(self) -> str:
        return f"docker-network-{self.name}.service"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {str(self.network)})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name and self.network == other.network


class VolumeSubdir:
    def __init__(
        self,
        path: str,
        user: Literal["root", "ctr"] = "root",
        group: Literal["root", "ctr"] = "root",
        mode: str = "0700",
    ) -> None:
        if os.path.isabs(path):
            raise ValueError(f"{self.__class__.__name__} paths may only be relative")
        self._volume: Optional[Volume] = None
        self.path = path
        self.user: Literal["root", "ctr"] = user
        self.group: Literal["root", "ctr"] = group
        self.mode = mode

    @property
    def src_abs_path(self) -> str:
        vol_path = self.volume.src
        if not os.path.isabs(vol_path):
            raise ValueError("parent volume is a named volume; cannot determine source path")
        return os.path.join(vol_path, self.path)

    @property
    def volume(self) -> "Volume":
        if self._volume is None:
            raise Exception("parent volume not set")
        return self._volume


class Volume:
    def __init__(
        self,
        name: str,
        src: str,
        dest: str,
        bind_mode: Literal["ro", "rw"] = "rw",
        user: Literal["root", "ctr"] = "root",
        group: Literal["root", "ctr"] = "root",
        mode: str = "0700",
        subdirs: Optional[List[VolumeSubdir]] = None,
    ) -> None:
        self.name = name
        self.src = src
        self.dest = dest
        self.bind_mode = bind_mode
        self.user: Literal["root", "ctr"] = user
        self.group: Literal["root", "ctr"] = group
        self.mode = mode
        self.subdirs: List[VolumeSubdir] = subdirs or []

        for s in self.subdirs:
            if s._volume is not None:
                raise Exception("assigned subdirectory already has a volume!")
            s._volume = self


class Container:
    def __init__(
        self,
        name: str,
        image: str,
        get_environment: Callable[[], Mapping[str, str]],
        deploy_config: Optional[Callable[[Pyinfra, "Container"], bool]],
        volumes: List[Volume],
        networks: List[ContainerNetwork],
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

        # In addition to environment variables, containers often have config
        # files that must be deployed in order to operate correctly.
        #
        # Configuration deployment needs to happen at a very specific time.
        # Files need to live inside a mounted volume, so that pyinfra can
        # deploy them to the host. That means the volume source directories
        # must exist. Additionally, the config files need to be readable by
        # the container's user, so that needs to exist, too.
        #
        # Rather than require the user to manage the correct ordering of
        # these operations, we expose this deploy_config attribute as
        # a Callable which receives a Pyinfra object and a Container
        # object.
        self.deploy_config = deploy_config

        self.volumes = volumes
        self._volumes_by_name = {v.name: v for v in volumes}
        self.networks = networks
        self.restart = restart
        self.ports = ports

        # For "linuxserver" containers, uid/gid will be implicitly passed
        # via the environment as "PUID" and "PGID".
        self.uid = uid
        self.gid = gid

        # These fields only apply to containers managed by systemd.
        self.max_restarts = max_restarts
        self.restart_sec = restart_sec

    @classmethod
    def restarting(
        cls,
        name: str,
        image: str,
        get_environment: Callable[[], Mapping[str, str]],
        deploy_config: Optional[Callable[[Pyinfra, "Container"], bool]],
        volumes: List[Volume],
        networks: List[ContainerNetwork],
        ports: List[str],
        uid: Optional[int],
        gid: Optional[int],
    ) -> "Container":
        """
        Creates a `Container` with some sensible defaults for restarting.
        """
        return cls(
            name,
            image,
            get_environment,
            deploy_config,
            volumes,
            networks,
            ports,
            uid,
            gid,
            restart="always",
            max_restarts=3,
            restart_sec=3,
        )

    def volume_named(self, volume_name: str) -> Volume:
        v = self._volumes_by_name.get(volume_name, None)
        if v is not None:
            return v
        raise ValueError(f"container {self.name} has no such volume: {volume_name}")
