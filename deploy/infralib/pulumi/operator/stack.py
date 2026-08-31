"""
infralib/pulumi/operator/stack -- Pulumi Stack Suboperator
==========================================================

This module contains the definition for the Pulumi stack sub-operator. It
performs stack-level operations.
"""

import os
import subprocess
from typing import Any, Protocol, TypeVar

from pulumi import automation as auto
from pulumi.automation._stack import RenameResult  # this is not publicly exported :-(

from ...deployment.project import all_projects
from ...deployment.stack import InfrastructureStack
from .tools import PulumiOperatorTools

_builtin_list = list

StackOperationResult = TypeVar(
    "StackOperationResult",
    bound=auto.RefreshResult
    | auto.PreviewResult
    | auto.UpResult
    | auto.DestroyResult
    | RenameResult,
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


class PulumiStackDescription:
    """
    Description of a Pulumi stack.
    """

    def __init__(
        self,
        stack: InfrastructureStack,
        code: bool,
        state: bool,
    ) -> None:
        # The InfrastructureStack being described.
        self.stack = stack

        # True if the InfrastructureStack is defined by a discovered project
        # where the stack is valid deployment target.
        self.code = code

        # True if the InfrastructureStack is defined in Pulumi's state backend.
        self.state = state

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return all(
            [
                self.stack == other.stack,
                self.code == other.code,
                self.state == other.state,
            ]
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}({self.stack}, code={self.code}, state={self.state})"


class PulumiStackOperator:
    """
    Performs operations on stacks.
    """

    def __init__(self, tools: PulumiOperatorTools) -> None:
        self.tools = tools

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
        pstack = self.tools.pulumi_stack(stack)
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

    def list(
        self,
    ) -> list[PulumiStackDescription]:
        """
        Lists available stacks.
        """
        project_stacks: dict[str, dict[str, PulumiStackDescription]] = dict()
        stack_desc: PulumiStackDescription | None

        for code_project in all_projects(include_state_only=False):
            project_dict = project_stacks.setdefault(code_project.name, dict())
            for target in code_project.deployment_targets():
                stack = InfrastructureStack(code_project, target)
                stack_desc = PulumiStackDescription(
                    stack,
                    code=True,
                    state=False,
                )
                project_dict[stack.name] = stack_desc

        ws = self.tools.pulumi_project_workspace("readonly")
        state_stacks = ws.list_stacks(include_all=True)

        for s in state_stacks:
            # Stack names are of the format:
            #
            #   organization/${PROJECT_NAME}/${STACK_NAME}
            _, project_name, stack_name = s.name.split("/")
            state_project = self.tools.try_state_only_project(project_name)
            project_dict = project_stacks.setdefault(project_name, dict())
            stack = InfrastructureStack.parse(state_project, stack_name)
            stack_desc = project_dict.get(stack.name, None)
            if stack_desc is None:
                stack_desc = PulumiStackDescription(
                    stack,
                    code=False,
                    state=True,
                )
                project_dict[stack.name] = stack_desc
            else:
                stack_desc.state = True

        stack_desc_list: list[PulumiStackDescription] = list()
        for project_dict in project_stacks.values():
            for stack_desc in project_dict.values():
                stack_desc_list.append(stack_desc)

        return sorted(
            stack_desc_list, key=lambda d: f"{d.stack.project.name}/{d.stack.name}"
        )

    def rename(
        self,
        source_stack: InfrastructureStack,
        destination_stack: InfrastructureStack,
        on_output: auto.OnOutput | None = None,
        on_error: auto.OnOutput | None = None,
        color: str | None = None,
    ) -> RenameResult:
        """
        Renames a stack.
        """

        def do_rename(stack: auto.Stack, **kwargs: Any) -> RenameResult:
            destination_full_name = kwargs["destination_full_name"]
            return stack.rename(
                stack_name=f"organization/{destination_full_name}",
                on_output=kwargs["on_output"],
                on_error=kwargs["on_error"],
            )

        return self._do_stack_operation(
            stack=source_stack,
            operation=do_rename,
            do_refresh=False,
            on_output=on_output,
            on_error=on_error,
            color=color,
            extra_args={"destination_full_name": destination_stack.full_name},
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
        self, stack: InfrastructureStack, command: _builtin_list[str]
    ) -> "subprocess.CompletedProcess[bytes]":
        """
        Synthesizes the Pulumi project directory, then launches the given
        shell command in that directory.
        """
        pstack = self.tools.pulumi_stack(stack)
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
