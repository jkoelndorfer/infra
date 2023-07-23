"""
lib/pyinfra
-----------

This module contains a facade for interacting with pyinfra.

Pyright [1] does not do a terribly good job providing autocompletion and proper
checking for pyinfra code. With a facade, we can simplify the exposed interface
to pyright and achieve some half-decent autocompletion.

Additionally, some reasonable defaults can be set on operations.

[1]: https://github.com/microsoft/pyright
"""

from functools import wraps
from typing import List, Optional, TypeVar

from pyinfra.api.operation import OperationMeta
from pyinfra.operations import apt, files, pacman, server, systemd

from .aws import aws_access_key_id as aws_access_key_id_f, aws_secret_access_key as aws_secret_access_key_f
from .operations.aws import s3_download


T = TypeVar("T", "Pyinfra", "PyinfraOperationWrapper")


def any_tags_selected(tags: List[str]) -> bool:
    """
    Returns True if any tags in `tags` are selected to be run.
    Returns False otherwise.
    """
    # TODO: Implement this.
    return True


def operation(f):
    """
    Wrapper for pyinfra facade operations to provide common functionality.
    """
    @wraps(f)
    def wrapped(self: "PyinfraOperationWrapper", *args, **kwargs):
        name = kwargs.get("name", None)
        if name is not None:
            kwargs["name"] = self.name(name)
        if not any_tags_selected(self.parent._tags):
            return
        return f(self, *args, **kwargs)
    return wrapped


class Pyinfra:
    def __init__(self, ctx: Optional[List[str]] = None, tags: Optional[List[str]] = None) -> None:
        self._ctxs: List[str] = ctx or []
        self._tags: List[str] = tags or []
        self.aws = PyinfraAws(self)
        self.apt = PyinfraApt(self)
        self.files = PyinfraFiles(self)
        self.pacman = PyinfraPacman(self)
        self.server = PyinfraServer(self)
        self.systemd = PyinfraSystemd(self)

    def __enter__(self) -> "Pyinfra":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

    def ctx(self, *ctxs: str) -> "Pyinfra":
        return self.__class__(ctx=[*self._ctxs, *ctxs])

    def tags(self, *tags: str) -> "Pyinfra":
        return self.__class__(tags=[*self._tags, *tags])


class PyinfraOperationWrapper:
    """
    Base class for Pyinfra operation wrappers.

    Allows attaching additional context to operations.
    """

    def __init__(self, parent: "Pyinfra") -> None:
        self.parent = parent

    def name(self, name: str) -> str:
        """
        Provides an operation name in accordance with the current contexts.
        """
        if self.name is not None:
            return f"[{' / '.join(self.parent._ctxs)}] {name}"
        else:
            return name


class PyinfraAws(PyinfraOperationWrapper):
    """
    Pyinfra facade over AWS.

    Pyinfra does not actually have AWS operations but there is at least one
    in this repo. For consistency, it is exposed through the same interface
    as other operations.
    """

    @operation
    def s3_download(
        self,
        *,
        name: str,
        src: str,
        dest: str,
        user: str = "root",
        group: str = "root",
        mode: str,
        sha256sum: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Downloads a file from S3 to the path given by `dest`.
        """
        return s3_download(
            name=name,
            src=src,
            dest=dest,
            user=user,
            group=group,
            mode=mode,
            sha256sum=sha256sum,
            aws_access_key_id=aws_access_key_id or aws_access_key_id_f(),
            aws_secret_access_key=aws_secret_access_key or aws_secret_access_key_f(),
            _sudo=_sudo,
        )


class PyinfraApt(PyinfraOperationWrapper):
    """
    Wraps pyinfra's apt operations.

    https://docs.pyinfra.com/en/2.x/operations/apt.html
    """

    @operation
    def deb(
        self,
        *,
        name: str,
        src: str,
        present: bool = True,
        force: bool = False,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's apt.deb operation.

        https://docs.pyinfra.com/en/2.x/operations/apt.html#apt-deb
        """
        return apt.deb(
            name=name,
            src=src,
            present=present,
            force=force,
            _sudo=_sudo,
        )  # pyright: ignore

    @operation
    def packages(
        self,
        *,
        name: str,
        packages: List[str],
        present: bool = True,
        latest: bool = False,
        update: bool = False,
        cache_time: Optional[int] = None,
        upgrade: bool = False,
        force: bool = False,
        no_recommends: bool = False,
        allow_downgrades: bool = False,
        extra_install_args: Optional[str] = None,
        extra_uninstall_args: Optional[str] = None,
        _sudo: Optional[bool] = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's apt.packages operation.

        https://docs.pyinfra.com/en/2.x/operations/apt.html#apt-packages
        """
        return apt.packages(
            name=name,
            packages=packages,
            present=present,
            latest=latest,
            update=update,
            cache_time=cache_time,
            upgrade=upgrade,
            force=force,
            no_recommends=no_recommends,
            allow_downgrades=allow_downgrades,
            extra_install_args=extra_install_args,
            extra_uninstall_args=extra_uninstall_args,
            _sudo=_sudo,
        )  # pyright: ignore


class PyinfraFiles(PyinfraOperationWrapper):
    """
    Wraps pyinfra's files operations.

    https://docs.pyinfra.com/en/2.x/operations/files.html
    """

    @operation
    def directory(
        self,
        *,
        name: str,
        path: str,
        present: bool = True,
        assume_present: bool = False,
        user: str,
        group: str,
        mode: str,
        recursive: bool = False,
        force: bool = False,
        force_backup: bool = True,
        force_backup_dir: Optional[str] = None,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's files.directory operation.

        https://docs.pyinfra.com/en/2.x/operations/files.html#files-directory
        """
        return files.directory(
            name=name,
            path=path,
            present=present,
            assume_present=assume_present,
            user=user,
            group=group,
            mode=mode,
            recursive=recursive,
            force=force,
            force_backup=force_backup,
            force_backup_dir=force_backup_dir,
            _sudo=_sudo,
        )  # pyright: ignore

    @operation
    def download(
        self,
        *,
        name: str,
        src: str,
        dest: str,
        user: str = "root",
        group: str = "root",
        mode: str,
        cache_time: Optional[int] = None,
        force: bool = False,
        sha256sum: str,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's files.download operation.

        https://docs.pyinfra.com/en/2.x/operations/files.html#files-download
        """
        return files.download(
            name=name,
            src=src,
            dest=dest,
            user=user,
            group=group,
            mode=mode,
            cache_time=cache_time,
            force=force,
            sha256sum=sha256sum,
            _sudo=_sudo,
        )  # pyright: ignore

    @operation
    def put(
        self,
        *,
        name: str,
        src: str,
        dest: str,
        user: str = "root",
        group: str = "root",
        mode: str,
        add_deploy_dir: bool = True,
        create_remote_dir: bool = True,
        force: bool = False,
        assume_exists: bool = False,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's files.put operation.

        https://docs.pyinfra.com/en/2.x/operations/files.html#files-put
        """
        return files.put(
            name=name,
            src=src,
            dest=dest,
            user=user,
            group=group,
            mode=mode,
            add_deploy_dir=add_deploy_dir,
            create_remote_dir=create_remote_dir,
            force=force,
            assume_exists=assume_exists,
            _sudo=_sudo,
        )  # pyright: ignore

    @operation
    def template(
        self,
        *,
        name: str,
        src: str,
        dest: str,
        user: str = "root",
        group: str = "root",
        mode: str,
        create_remote_dir: bool = True,
        _sudo: bool = True,
        **data,
    ) -> OperationMeta:
        """
        Wraps pyinfra's files.template operation.

        https://docs.pyinfra.com/en/2.x/operations/files.html#files-template
        """
        return files.template(
            name=name,
            src=src,
            dest=dest,
            user=user,
            group=group,
            mode=mode,
            create_remote_dir=create_remote_dir,
            _sudo=_sudo,
            **data,
        )  # pyright: ignore


class PyinfraPacman(PyinfraOperationWrapper):
    """
    Wraps pyinfra's pacman operations.

    https://docs.pyinfra.com/en/2.x/operations/pacman.html
    """

    @operation
    def packages(
        self,
        *,
        name: str,
        packages: List[str],
        present: bool = True,
        update: bool = False,
        upgrade: bool = False,
        _sudo: bool = True,
    ) -> OperationMeta:
        return pacman.packages(
            name=name,
            packages=packages,
            present=present,
            update=update,
            upgrade=upgrade,
            _sudo=_sudo,
        )  # pyright: ignore


class PyinfraServer(PyinfraOperationWrapper):
    """
    Wraps pyinfra's server operations.

    https://docs.pyinfra.com/en/2.x/operations/server.html
    """

    @operation
    def group(
        self,
        *,
        name: str,
        group: str,
        present: bool = True,
        system: bool = False,
        gid: Optional[int] = None,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's server.group operation.

        https://docs.pyinfra.com/en/2.x/operations/server.html#server-group
        """
        return server.group(
            name=name,
            group=group,
            present=present,
            system=system,
            gid=gid,
            _sudo=_sudo,
        )  # pyright: ignore

    @operation
    def shell(
        self,
        *,
        name: str,
        commands: List[str],
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's server.shell operation.

        https://docs.pyinfra.com/en/2.x/operations/server.html#server-shell
        """
        return server.shell(
            name=name,
            commands=commands,
            _sudo=_sudo,
        )  # pyright: ignore

    @operation
    def user(
        self,
        *,
        name: str,
        user: str,
        present: bool = True,
        home: Optional[str] = None,
        shell: Optional[str] = None,
        group: Optional[str] = None,
        groups: Optional[List[str]] = None,
        public_keys: Optional[List[str]] = None,
        delete_keys: bool = False,
        ensure_home: bool = True,
        system: bool = False,
        uid: Optional[int] = None,
        comment: Optional[str] = None,
        add_deploy_dir: bool = True,
        unique: bool = True,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's server.user operation.

        https://docs.pyinfra.com/en/2.x/operations/server.html#server-user
        """
        return server.user(
            name=name,
            user=user,
            present=present,
            home=home,
            shell=shell,
            group=group,
            groups=groups,
            public_keys=public_keys,
            delete_keys=delete_keys,
            ensure_home=ensure_home,
            system=system,
            uid=uid,
            comment=comment,
            add_deploy_dir=add_deploy_dir,
            unique=unique,
            _sudo=_sudo,
        )  # pyright: ignore


class PyinfraSystemd(PyinfraOperationWrapper):
    """
    Wraps pyinfra's systemd operations.

    https://docs.pyinfra.com/en/2.x/operations/systemd.html
    """

    @operation
    def daemon_reload(
        self,
        *,
        name: str,
        user_mode: bool = False,
        machine: Optional[str] = None,
        user_name: Optional[str] = None,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's systemd.daemon_reload operation.

        https://docs.pyinfra.com/en/2.x/operations/systemd.html#systemd-daemon-reload
        """
        return systemd.daemon_reload(
            name=name,
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
            _sudo=_sudo,
        )  # pyright: ignore

    @operation
    def service(
        self,
        *,
        name: str,
        service: str,
        running: bool = True,
        restarted: bool = False,
        reloaded: bool = False,
        enabled: Optional[bool] = None,
        daemon_reload: bool = False,
        user_mode: bool = False,
        machine: Optional[str] = None,
        user_name: Optional[str] = None,
        _sudo: bool = True,
    ) -> OperationMeta:
        """
        Wraps pyinfra's systemd.service operation.

        https://docs.pyinfra.com/en/2.x/operations/systemd.html#systemd-service
        """
        return systemd.service(
            name=name,
            service=service,
            running=running,
            restarted=restarted,
            reloaded=reloaded,
            enabled=enabled,
            daemon_reload=daemon_reload,
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
            _sudo=_sudo,
        )  # pyright: ignore
