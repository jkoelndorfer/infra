"""
cli/output
==========

This module contains code to manage output from the CLI.
"""

from functools import partial
import sys
from typing import Callable

from pulumi.automation import OnOutput


class PulumiOutputHandler:
    """
    PulumiOutputHandler manages output froom Pulumi.
    """

    # Pulumi prints a warning when there is no GCP project configured on a
    # a GCP provider. [1]:
    #
    # > warning: unable to detect a global setting for GCP Project.
    # > Pulumi will rely on per-resource settings for this operation.
    # > Set the GCP Project by using:
    # >     `pulumi config set gcp:project <project>`
    # > If you would like to disable this warning use:
    # >     `pulumi config set gcp:disableGlobalProjectWarning true`
    #
    # The suggestion above doesn't actually work unless you're using a
    # default provider. We don't use a default provider, because we don't
    # want there to be resources created in the wrong place if multiple
    # stacks are upped in one process. Explicit is good.
    #
    # Since we cannot make Pulumi stop printing the messages, we hide them.
    #
    # [1]: Note that the message contains terminal escape sequences to colorize
    #      "warning". Be careful with when selecting strings to match against,
    #      since those strings might contain invisible escape sequences.
    GCP_FILTERED_OUTPUT_START = "unable to detect a global setting for GCP Project."
    GCP_FILTERED_OUTPUT_END = "`pulumi config set gcp:disableGlobalProjectWarning true`"

    def __init__(self) -> None:
        self._filtering_output = False
        self._filtering_error = False
        self.output_handler: OnOutput = print
        self.error_handler: OnOutput = partial(print, file=sys.stderr)

    def _get_output_filtering(self) -> bool:
        """
        Returns the True if filtering is active on the output stream,
        False otherwise.
        """
        return self._filtering_output

    def _set_output_filtering(self, filtering: bool) -> None:
        """
        Enables or disables filtering on the output stream.
        """
        self._filtering_output = filtering

    def _get_error_filtering(self) -> bool:
        """
        Returns the True if filtering is active on the error stream,
        False otherwise.
        """
        return self._filtering_error

    def _set_error_filtering(self, filtering: bool) -> None:
        """
        Enables or disables filtering on the error stream.
        """
        self._filtering_error = filtering

    def _should_begin_filtering(self, line: str) -> bool:
        """
        Returns True if the provided line indicates that filtering
        should be activated, False otherwise.
        """
        return self.GCP_FILTERED_OUTPUT_START in line

    def _should_stop_filtering(self, line: str) -> bool:
        """
        Returns True if the provided line indicates that filtering
        should be deactivated, False otherwise.
        """
        return self.GCP_FILTERED_OUTPUT_END in line

    def _handle_output(
        self,
        line: str,
        handler: Callable[[str], None],
        get_filtering: Callable[[], bool],
        set_filtering: Callable[[bool], None],
    ) -> None:
        """
        Handles output from the output and error streams.
        """
        if self._should_begin_filtering(line):
            set_filtering(True)

        if not get_filtering():
            handler(line)

        if self._should_stop_filtering(line):
            set_filtering(False)

    def on_output(self, line: str) -> None:
        """
        Handler suitable for passing to Pulumi stack methods that accept
        an on_output parameter.
        """
        return self._handle_output(
            line,
            self.output_handler,
            self._get_output_filtering,
            self._set_output_filtering,
        )

    def on_error(self, line: str) -> None:
        """
        Handler suitable for passing to Pulumi stack methods that accept
        an on_error parameter.
        """
        return self._handle_output(
            line,
            self.error_handler,
            self._get_error_filtering,
            self._set_error_filtering,
        )
