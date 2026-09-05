"""
infralib/pulumi/export -- Pulumi Export Helpers
===============================================

This module contains helper code related to stack exports.
"""

from typing import Any

from pulumi import export, Output, Resource


def exportable_resource(
    resource: Resource | Output[Any],
    attrs: list[str],
    addl: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Converts the resource to an exportable dictionary with a subset of its attributes.
    Pulumi documentation recommends [1] that entire resources are not exported:

    > Note: If you export an actual resource, it too will be JSON serialized.
    > This usually isn’t what you want, especially because some resources are
    > quite large. For example, if you only want to export the resource’s ID
    > or name, just export those properties directly.

    Attribute types and names are preserved. This makes the outputs "look like"
    an actual resource, which creates consistency.

    If the "addl" dictionary is specified, additional keys are set on the
    resulting dictionary. These keys will override actual resource attributes
    if there is overlap.

    [1]: https://www.pulumi.com/docs/iac/concepts/stacks/#outputs
    """

    if addl is None:
        addl = dict()

    output = dict()
    for a in attrs:
        output[a] = getattr(resource, a)

    output.update(addl)

    return output


def export_resource(
    name: str,
    resource: Resource | Output[Any],
    attrs: list[str],
    addl: dict[str, Any] | None = None,
) -> None:
    """
    Exports the resource with a subset of its attributes. See also exportable_resource.
    """

    export(name, exportable_resource(resource, attrs, addl))
