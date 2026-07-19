"""
infralib/pulumi/name -- Pulumi Names
====================================

This module contains code to verify that names meet Pulumi requirements.
"""

import re

pulumi_name_regex = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")

_logical_name_replace_regex = re.compile(r"[^A-Za-z0-9_-]")


def is_project_name(s: str) -> bool:
    """
    Returns True if the given string is a valid Pulumi project name; False otherwise.

    Pulumi documentation does not specify project name constraints. See the source
    code [1] instead, where the comment reads:

    >   - must be non-empty
    >   - must be at most 100 characters
    >   - must contain only alphanumeric characters,
    >     hyphens, underscores, and periods (see [IsName])

    [1]: https://github.com/pulumi/pulumi/blob/5593b7bb2176451387f7449b3a60e39366938833/sdk/go/common/tokens/project.go
    """
    return pulumi_name_regex.match(s) is not None


def is_stack_name(s: str) -> bool:
    """
    Returns True if the given string is a valid Pulumi project name; False otherwise.

    Pulumi documentation describes stack name restrictions [2]:

    > The stack name must be unique within a project. Stack names may only contain
    > alphanumeric characters, hyphens, underscores, or periods.

    [2]: https://www.pulumi.com/docs/iac/concepts/stacks/#create-stack
    """
    return is_project_name(s)


def to_logical_name(s: str) -> str:
    """
    Given an arbitrary string s, converts the string to a valid Pulumi logical
    name identifier.
    """
    return _logical_name_replace_regex.sub("_", s)
