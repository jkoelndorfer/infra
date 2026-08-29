"""
infralib/pulumi/operator/tools -- Pulumi Operator Tools
=======================================================

This module contains the definition for Pulumi operator toolkit.

The operator toolkit provides access to objects and configuration that are
accessible to the top-level operator and all sub-operators.
"""

from tempfile import TemporaryDirectory as RealTemporaryDirectory
from typing import Any, TYPE_CHECKING

from pulumi import automation as auto

from ...config import InfrastructureConfiguration
from ...deployment.context import DeploymentContext
from ...deployment.project import InfrastructureProjectName
from ...deployment.stack import InfrastructureStack
from ...error import UndeclaredDependencyError
from ..backend import BackendProvider
from ..provider import ProviderFactory
from ..types import StackOutputResolver

if TYPE_CHECKING:
    TemporaryDirectory = RealTemporaryDirectory[str]
else:
    TemporaryDirectory = RealTemporaryDirectory


class PulumiOperatorTools:
    """
    Toolkit that is provided to the top-level Pulumi operator and sub-operators.
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

        # A list of created work directories. These are temporary, and are
        # cleaned up when cleanup() is called.
        self._work_dirs: list[TemporaryDirectory] = list()

        # A map of project name to Pulumi workspace. Used as a cache to
        # avoid unnecessarily recreating Pulumi project workspaces.
        self._proj_ws: dict[str, auto.LocalWorkspace] = dict()

        # A map of stack name to constructed Pulumi stack. Used as a
        # cache to avoid unnecessarily recreating Pulumi stack objects.
        self._pstacks: dict[str, auto.Stack] = dict()

    def cleanup(self) -> None:
        """
        Cleans up after created work directories.
        """
        self._proj_ws = dict()
        self._pstacks = dict()

        for d in self._work_dirs:
            d.cleanup()
        self._work_dirs = list()

    def project_settings(
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

        work_dir = self.work_dir()
        ws = auto.LocalWorkspace(
            work_dir=work_dir.name,
            project_settings=self.project_settings(project_name),
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
        work_dir = self.work_dir()
        s = auto.create_or_select_stack(
            stack_name=stack.name,
            project_name=stack.project.name,
            program=self.stack_program(stack),
            opts=auto.LocalWorkspaceOptions(
                project_settings=self.project_settings(stack.project.name),
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

    def stack_output_resolver(
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

    def stack_program(self, stack: InfrastructureStack) -> auto.PulumiFn:
        """
        Given an InfrastructureStack, returns a function that accepts no arguments
        and invokes the project's `pulumi_program` method.
        """

        def pulumi_fn() -> None:
            dctx = DeploymentContext(
                stack.target,
                self.config,
                self.provider_factory,
                self.stack_output_resolver(stack),
            )
            project = stack.project(
                dctx,
                **self.project_kwargs,
            )
            return project.pulumi_program()

        return pulumi_fn

    def work_dir(self) -> TemporaryDirectory:
        """
        Creates a work directory for a Pulumi workspace.

        Work directories are cleaned up when cleanup() is called.
        """
        work_dir = TemporaryDirectory(
            prefix="infralib-pulumi-", ignore_cleanup_errors=True, delete=False
        )
        self._work_dirs.append(work_dir)

        return work_dir
