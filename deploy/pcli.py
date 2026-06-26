#!/usr/bin/env -S uv run --script

"""
pulumi -- deployment command-line interface to Pulumi
=====================================================

This script is the primary interface to Pulumi in this repository. It provides
common scaffolding for Pulumi projects and their programs. Pulumi's Automation API
[1] is heavily used.

[1]: https://www.pulumi.com/docs/reference/pkg/python/pulumi/
"""

from argparse import ArgumentParser


class PulumiApp:
    """
    Application that wraps Pulumi and provides standard stack configuration.
    """

    def configure_argparser(self) -> None:
        """
        Configures the ArgumentParser for this application.
        """
        a = ArgumentParser()
        a.add_argument(
            "project",
            action="store",
            help="the name of the Pulumi project to operate against",
        )
        a.add_argument(
            "-e",
            "--env",
            "--environment",
            action="store",
            choices=["dev", "prod"],
            help="the name of the environment to operate against",
        )
        a.add_argument(
            "-r",
            "--region",
            action="store",
            help="the name of the region where infrastructure is deployed",
        )
