"""
projects.homelab.traefik.config
===============================

This module contains configuration for the homelab Traefik project.
"""


class TraefikConfiguration:
    """
    Class defining common Traefik configuration.
    """

    cert_resolver = "homelab"
    """
    The name of the certificate resolver.

    Handles automatically requesting short-lived certificates via Let's Encrypt.
    """

    insecure_entrypoint = "web"
    """
    The name of the Traefik HTTP entrypoint.

    All requests are automatically redirected to HTTPS.
    """

    secure_entrypoint = "websecure"
    """
    The name of the Traefik HTTPS entrypoint.
    """

    http_port = 80
    """
    The port on which HTTP traffic is served by Traefik.
    """

    https_port = 443
    """
    The port on which HTTPS traffic is served by Traefik.
    """
