"""
dyndns
======

AWS Lambda function that keeps a single Route 53 A record pointed at a client's
public IPv4 address. It is invoked through a Lambda function URL using a subset of
the dyndns2 protocol [1].

The record, its zone, and the client's credentials are fixed by the deployment
through environment variables. Requests for any other hostname are rejected, and
the function's IAM role can only UPSERT that one A record.

NOTE: This directory is not a Python package on purpose. It is packaged into the
Lambda function by the dns.dyndns project, and must not be imported by project
discovery.

[1]: https://help.dyn.com/remote-access-api/perform-update/
"""

from base64 import b64decode
from collections.abc import Mapping
from binascii import Error as BinasciiError
from dataclasses import dataclass, field
from functools import cache
from hashlib import sha256
from hmac import compare_digest
from http import HTTPStatus
from ipaddress import AddressValueError, IPv4Address
import logging
import os
from typing import Any, Protocol, Self

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class Route53Client(Protocol):
    """
    The subset of the boto3 Route 53 client that this function uses.
    """

    def change_resource_record_sets(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class Settings:
    """
    Settings for the function, read from its environment.
    """

    # The fully-qualified name of the A record that is updated.
    hostname: str

    # The ID of the Route 53 hosted zone holding the record.
    zone_id: str

    # The TTL, in seconds, of the record.
    ttl: int

    # The username that clients must authenticate with.
    username: str

    # The hex-encoded SHA-256 digest of the password that clients must authenticate
    # with. The password itself is not given to the function.
    password_sha256: str = field(repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Self:
        return cls(
            hostname=_normalize_hostname(env["DYNDNS_HOSTNAME"]),
            zone_id=env["DYNDNS_ZONE_ID"],
            ttl=int(env["DYNDNS_TTL"]),
            username=env["DYNDNS_USERNAME"],
            password_sha256=env["DYNDNS_PASSWORD_SHA256"],
        )


@dataclass(frozen=True)
class Response:
    """
    A dyndns2 response. The body is the dyndns2 return code, such as "good" or
    "badauth".
    """

    status: HTTPStatus
    body: str

    def to_function_url(self) -> dict[str, Any]:
        """
        Returns the response in the format a Lambda function URL expects.
        """
        return {
            "statusCode": self.status.value,
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
            "body": f"{self.body}\n",
        }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Entry point for the Lambda function.
    """
    try:
        response = handle(event, Settings.from_env(os.environ), _route53_client())
    except Exception:
        logger.exception("Unhandled error while handling dyndns request")
        response = Response(HTTPStatus.INTERNAL_SERVER_ERROR, "911")

    return response.to_function_url()


def handle(event: dict[str, Any], settings: Settings, r53: Route53Client) -> Response:
    """
    Handles a dyndns2 update request delivered through a Lambda function URL [1].

    [1]: https://docs.aws.amazon.com/lambda/latest/dg/urls-invocation.html#urls-payloads
    """
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method not in ("GET", "POST"):
        return Response(HTTPStatus.METHOD_NOT_ALLOWED, "badrequest")

    # Function URLs lowercase header names.
    headers = event.get("headers") or {}
    if not _authorized(headers.get("authorization"), settings):
        logger.warning("Rejected request with invalid credentials")
        return Response(HTTPStatus.UNAUTHORIZED, "badauth")

    params = event.get("queryStringParameters") or {}
    hostname = params.get("hostname")
    if not hostname:
        return Response(HTTPStatus.BAD_REQUEST, "notfqdn")
    if _normalize_hostname(hostname) != settings.hostname:
        logger.warning("Rejected update for unmanaged hostname %r", hostname)
        return Response(HTTPStatus.FORBIDDEN, "nohost")

    try:
        ip = IPv4Address(params.get("myip") or "")
    except AddressValueError:
        return Response(HTTPStatus.BAD_REQUEST, "badrequest")
    if not ip.is_global:
        logger.warning("Rejected update to non-global address %s", ip)
        return Response(HTTPStatus.BAD_REQUEST, "badrequest")

    logger.info("Updating %s to %s", settings.hostname, ip)
    r53.change_resource_record_sets(
        HostedZoneId=settings.zone_id,
        ChangeBatch={
            "Comment": "dyndns update",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": settings.hostname,
                        "Type": "A",
                        "TTL": settings.ttl,
                        "ResourceRecords": [{"Value": str(ip)}],
                    },
                }
            ],
        },
    )

    return Response(HTTPStatus.OK, f"good {ip}")


def _authorized(header: str | None, settings: Settings) -> bool:
    """
    Returns True if an Authorization header holds the configured Basic credentials.

    NOTE: Never log the header. It holds the client's password.
    """
    if header is None:
        return False

    scheme, _, encoded = header.strip().partition(" ")
    if scheme.casefold() != "basic":
        return False

    try:
        decoded = b64decode(encoded.strip(), validate=True).decode("utf-8")
    except BinasciiError, UnicodeDecodeError:
        return False

    username, sep, password = decoded.partition(":")
    if not sep:
        return False

    password_sha256 = sha256(password.encode("utf-8")).hexdigest()

    # Both comparisons run, so that timing does not reveal which one failed.
    username_ok = compare_digest(username.encode("utf-8"), settings.username.encode())
    password_ok = compare_digest(password_sha256, settings.password_sha256)
    return username_ok and password_ok


def _normalize_hostname(hostname: str) -> str:
    return hostname.strip().rstrip(".").casefold()


@cache
def _route53_client() -> Route53Client:  # pragma: no cover
    # boto3 is provided by the Lambda runtime, but is not a dependency of the
    # deployment code.
    import boto3

    client: Route53Client = boto3.client("route53")
    return client
