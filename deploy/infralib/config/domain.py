"""
infralib/config/domain -- Domain Configuration
==============================================

This file defines data types for domain configuration.
"""

from dataclasses import dataclass
from typing import Any, cast, ClassVar, get_args, Literal, Self

from ..deployment.target import DeploymentTarget, Environment

DomainID = str
DKIMKeyType = Literal["rsa", "ed25519"]


@dataclass
class DKIMv1:
    """
    DKIM version 1 configuration for a domain.
    """

    version: ClassVar[str] = "DKIM1"
    selector: str
    key_type: DKIMKeyType
    public_key: str

    def __str__(self) -> str:
        return "; ".join(
            [
                f"v={self.version}",
                f"k={self.key_type}",
                f"p={self.public_key}",
            ]
        )

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Self:
        key_type = d["key_type"]
        if key_type not in get_args(DKIMKeyType):
            raise ValueError(f"invalid DKIM key type {key_type}")
        key_type = cast(DKIMKeyType, key_type)

        return cls(
            selector=d["selector"],
            key_type=key_type,
            public_key=d["public_key"],
        )


class Domain:
    """
    Configuration representing a DNS domain.
    """

    def __init__(
        self,
        id: DomainID,
        domain: str,
        description: str,
        dkim_v1: list[DKIMv1],
        google_site_verification: str | None,
    ) -> None:
        self.id = id
        self._domain = domain
        self.description = description
        self.dkim_v1 = dkim_v1
        self.google_site_verification = google_site_verification

    def domain_for(self, target: DeploymentTarget) -> str:
        """
        Given a deployment target, returns the full apex domain for that target.

        If the domain name is "example.com", the returned domain is "example.com"
        for prod and "dev.example.com" for dev.
        """
        host = self.host_for(target)
        if host:
            return f"{host}.{self._domain}"

        return self._domain

    @classmethod
    def host_for(cls, target: DeploymentTarget) -> str:
        """
        Given a deployment target, returns the host portion only for that target.
        """
        host = ""
        if target.environment != Environment.PROD:
            host = f"{target.environment}.{host}"

        if target.region is not None:
            host = f"{target.region}.{host}"

        return host.rstrip(".")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(
            d["id"],
            d["domain"],
            d["description"],
            [DKIMv1.from_dict(i) for i in d.get("dkim_v1", list())],
            d.get("google_site_verification", None),
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, domain={self._domain})"


Domains = dict[DomainID, Domain]
