"""
infralib/pulumi/operator -- Pulumi Operator
===========================================

This module contains the Pulumi operator, which performs tasks like:

* Instantiating correctly configured Pulumi stacks
* Refreshing and upping the stacks
* Providing Pulumi programs a mechanism to look up outputs from other stacks
"""

import os
import subprocess
from tempfile import TemporaryDirectory as RealTemporaryDirectory
from typing import Any, Protocol, TYPE_CHECKING, TypeVar

from pulumi import automation as auto

from ..config import InfrastructureConfiguration
from ..deployment.context import DeploymentContext
from ..deployment.project import InfrastructureProjectName
from ..deployment.stack import InfrastructureStack
from ..error import UndeclaredDependencyError
from .backend import BackendProvider
from .provider import ProviderFactory
from .types import StackOutputResolver

if TYPE_CHECKING:
    TemporaryDirectory = RealTemporaryDirectory[str]
else:
    TemporaryDirectory = RealTemporaryDirectory


StackOperationResult = TypeVar(
    "StackOperationResult",
    bound=auto.RefreshResult | auto.PreviewResult | auto.UpResult | auto.DestroyResult,
)


class _PulumiStackOperation[StackOperationResult](Protocol):
    """
    Defines the interface for a PulumiStackOperation.
    """

    def __call__(
        self,
        stack: auto.Stack,
        **kwargs: Any,
    ) -> StackOperationResult:
        raise NotImplementedError("protocol does not implement concrete methods")


class PulumiOperator:
    """
    PulumiOperator is responsible for interfacing with the Pulumi automation API.
    It provides an interface to instantiate stacks configured with a proper backend,
    refreshing and upping stacks, and lookup of outputs in dependent stacks.

    See the Pulumi Python SDK.

    https://www.pulumi.com/docs/reference/pkg/python/pulumi/
    """

    def __init__(
        self,
        config: InfrastructureConfiguration,
        backend_provider: BackendProvider,
        provider_factory: ProviderFactory,
        project_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.config = config
        self.backend_provider = backend_provider
        self.provider_factory = provider_factory
        self.project_kwargs = project_kwargs or dict()

        # A map of project name to Pulumi workspace. Used as a cache to
        # avoid unnecessarily recreating Pulumi project workspaces.
        self._proj_ws: dict[str, auto.LocalWorkspace] = dict()

        # A map of stack name to constructed Pulumi stack. Used as a
        # cache to avoid unnecessarily recreating Pulumi stack objects.
        self._pstacks: dict[str, auto.Stack] = dict()

        # A list of Pulumi temporary directories to clean up when cleanup()
        # is called.
        self._cleanup_dirs: list[TemporaryDirectory] = list()

    def cleanup(self) -> None:
        """
        Cleans up after created stacks. In particular, this removes work directories created
        by the automation API.
        """
        self._pstacks = dict()
        for d in self._cleanup_dirs:
            d.cleanup()

    def _do_stack_operation(
        self,
        stack: InfrastructureStack,
        operation: _PulumiStackOperation[StackOperationResult],
        on_output: auto.OnOutput | None = None,
        on_error: auto.OnOutput | None = None,
        color: str | None = None,
        do_refresh: bool = True,
        output_refresh: bool = False,
        run_program: bool = True,
        extra_args: dict[str, Any] | None = None,
    ) -> StackOperationResult:
        """
        Performs an operation against a Pulumi stack.
        """
        pstack = self.pulumi_stack(stack)
        extra_args = extra_args or dict()

        # Pulumi does not implicitly refresh infrastructure state before performing
        # operations. Refreshing is usually desired, just in case there are any changes.
        # Let's do it here by default.
        if do_refresh:
            if output_refresh:
                pstack.refresh(
                    run_program=run_program,
                    on_output=on_output,
                    on_error=on_error,
                    color=color,
                )
            else:
                pstack.refresh()

        return operation(
            pstack,
            run_program=run_program,
            on_output=on_output,
            on_error=on_error,
            color=color,
            **extra_args,
        )

    def destroy(
        self,
        stack: InfrastructureStack,
        on_output: auto.OnOutput | None = None,
        on_error: auto.OnOutput | None = None,
        color: str | None = None,
        do_refresh: bool = True,
        output_refresh: bool = False,
        run_program: bool = True,
    ) -> auto.DestroyResult:
        """
        Destroys the given InfrastructureStack.
        """

        def do_destroy(stack: auto.Stack, **kwargs: Any) -> auto.DestroyResult:
            return stack.destroy(**kwargs)

        return self._do_stack_operation(
            stack=stack,
            operation=do_destroy,
            run_program=run_program,
            on_output=on_output,
            on_error=on_error,
            color=color,
            do_refresh=do_refresh,
            output_refresh=output_refresh,
        )

    def preview(
        self,
        stack: InfrastructureStack,
        on_output: auto.OnOutput | None = None,
        on_error: auto.OnOutput | None = None,
        color: str | None = None,
        do_refresh: bool = True,
        output_refresh: bool = False,
        run_program: bool = True,
        diff: bool = True,
    ) -> auto.PreviewResult:
        """
        Previews the given InfrastructureStack.
        """

        def do_preview(stack: auto.Stack, **kwargs: Any) -> auto.PreviewResult:
            return stack.preview(**kwargs)

        return self._do_stack_operation(
            stack=stack,
            operation=do_preview,
            run_program=run_program,
            on_output=on_output,
            on_error=on_error,
            color=color,
            do_refresh=do_refresh,
            output_refresh=output_refresh,
            extra_args={"diff": diff},
        )

    def preview_destroy(
        self,
        stack: InfrastructureStack,
        on_output: auto.OnOutput | None = None,
        on_error: auto.OnOutput | None = None,
        color: str | None = None,
        run_program: bool = True,
        do_refresh: bool = True,
    ) -> auto.DestroyResult:
        """
        Previews a destroy for the given InfrastructureStack.
        """

        def do_preview_destroy(stack: auto.Stack, **kwargs: Any) -> auto.DestroyResult:
            return stack.destroy(**kwargs, preview_only=True)

        return self._do_stack_operation(
            stack=stack,
            operation=do_preview_destroy,
            run_program=run_program,
            on_output=on_output,
            on_error=on_error,
            color=color,
            do_refresh=do_refresh,
        )

    def shell(
        self, stack: InfrastructureStack, command: list[str]
    ) -> "subprocess.CompletedProcess[bytes]":
        """
        Synthesizes the Pulumi project directory, then launches the given
        shell command in that directory.
        """
        pstack = self.pulumi_stack(stack)
        work_dir = pstack.workspace.work_dir

        shell_env = os.environ.copy()
        shell_env["INFRALIB_PULUMI_PROJECT_DIR"] = work_dir

        return subprocess.run(
            args=command,
            cwd=work_dir,
            env=shell_env,
        )

    def up(
        self,
        stack: InfrastructureStack,
        on_output: auto.OnOutput | None = None,
        on_error: auto.OnOutput | None = None,
        color: str | None = None,
        do_refresh: bool = True,
        output_refresh: bool = False,
        run_program: bool = True,
    ) -> auto.UpResult:
        """
        Ups the given InfrastructureStack.
        """

        def do_up(stack: auto.Stack, **kwargs: Any) -> auto.UpResult:
            return stack.up(**kwargs)

        return self._do_stack_operation(
            stack=stack,
            operation=do_up,
            run_program=run_program,
            on_output=on_output,
            on_error=on_error,
            color=color,
            do_refresh=do_refresh,
            output_refresh=output_refresh,
        )

    def _stack_output_resolver(
        self, requesting_stack: InfrastructureStack
    ) -> StackOutputResolver:
        """
        Given an InfrastructureStack that will *request outputs*, returns a
        function that can be used by a program to fetch outputs from a
        dependent stack.

        The resolver will ensure that the stack whose outputs are accessed
        is properly declared as a dependency of the requesting stack.
        """

        permitted_stacks = requesting_stack.project.dependencies(
            requesting_stack.target
        )

        def stack_outputs(stack: InfrastructureStack) -> auto.OutputMap:
            if stack not in permitted_stacks:
                raise UndeclaredDependencyError(
                    requesting_stack=requesting_stack,
                    outputting_stack=stack,
                )

            return self.pulumi_stack(stack).outputs()

        return stack_outputs

    def _stack_program(self, stack: InfrastructureStack) -> auto.PulumiFn:
        """
        Given an InfrastructureStack, returns a function that accepts no arguments
        and invokes the project's `pulumi_program` method.
        """

        def pulumi_fn() -> None:
            dctx = DeploymentContext(
                stack.target,
                self.config,
                self.provider_factory,
                self._stack_output_resolver(stack),
            )
            project = stack.project(
                dctx,
                **self.project_kwargs,
            )
            return project.pulumi_program()

        return pulumi_fn

    def _project_settings(
        self,
        project_name: str | InfrastructureProjectName,
    ) -> auto.ProjectSettings:
        """
        Returns ProjectSettings suitable for the given project.
        """
        return auto.ProjectSettings(
            name=project_name,
            runtime="python",
            backend=auto.ProjectBackend(
                url=self.backend_provider.pulumi_url(project_name)
            ),
        )

    def pulumi_project_workspace(
        self,
        project_name: str | InfrastructureProjectName,
    ) -> auto.LocalWorkspace:
        ws = self._proj_ws.get(project_name, None)
        if ws is not None:
            return ws

        work_dir = self._work_dir()
        ws = auto.LocalWorkspace(
            work_dir=work_dir.name,
            project_settings=self._project_settings(project_name),
        )
        self._proj_ws[project_name] = ws

        return ws

    def pulumi_stack(
        self,
        stack: InfrastructureStack,
    ) -> auto.Stack:
        """
        Converts an InfrastructureStack to a Pulumi Stack.
        """
        s = self._pstacks.get(stack.full_name, None)
        if s is not None:
            return s

        # NOTE: It might be tempting to minimize the number of created Pulumi
        # workspaces here. Each workspace corresponds to a project, so we only
        # "need" one workspace per project. The issue is that workspaces maintain
        # state. Within a workspace, there is a currently selected stack. Some
        # operations may use this selected stack implicitly. Rather than have to
        # worry about managing workspace state (particularly if there is ever
        # concurrency), we simply create a dedicated workspace per-stack.
        work_dir = self._work_dir()
        s = auto.create_or_select_stack(
            stack_name=stack.name,
            project_name=stack.project.name,
            program=self._stack_program(stack),
            opts=auto.LocalWorkspaceOptions(
                project_settings=self._project_settings(stack.project.name),
                work_dir=work_dir.name,
            ),
        )

        # Disable Pulumi resource auto-naming. This prevents resources from having
        # a randomly-generated suffix applied to the name.
        #
        # https://www.pulumi.com/docs/iac/concepts/resources/names/#autonaming-configuration
        s.set_config(
            "pulumi:autonaming.mode",
            auto.ConfigValue(value="verbatim"),
            path=True,
        )

        # Disable default providers. We want to ensure our providers are always
        # explicitly configured. We can write our own helpers to auto-configure
        # a provider used in multiple projects.
        #
        # https://www.pulumi.com/docs/iac/concepts/providers/#disabling-default-providers
        s.set_config(
            "pulumi:disable-default-providers[0]",
            auto.ConfigValue(value="*"),
            path=True,
        )

        self._pstacks[stack.full_name] = s
        return s

    def _work_dir(self) -> TemporaryDirectory:
        """
        Creates a temporary Pulumi work directory.
        """
        work_dir = TemporaryDirectory(
            prefix="infralib-pulumi-", ignore_cleanup_errors=True, delete=False
        )
        self._cleanup_dirs.append(work_dir)

        return work_dir
