"""
projects.homelab.kubernetes.secret
==================================

This module contains helpers for working with Kubernetes secrets.
"""

from base64 import b64decode


def decode_secret(v: str) -> str:
    """
    Given a Kubernetes secret data field, returns the plaintext value.

    For a pulumi_kubernetes.core.v1.Secret resource called `secret`:

        secret.data.apply(lambda d: decode_secret(d["secretField"]))

    The resulting value is the plaintext of the secret's data.secretField.
    """
    return b64decode(v).decode("utf-8")
