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

from ...deployment.stack import InfrastructureStack
from .tools import PulumiOperatorTools

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
        self, stack: InfrastructureStack, command: list[str]
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
