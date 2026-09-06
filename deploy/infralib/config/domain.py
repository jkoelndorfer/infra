"""
infralib/config/domain -- Domain Configuration
==============================================

This file defines data types for domain configuration.
"""

from dataclasses import dataclass
from typing import Any, cast, ClassVar, get_args, Literal, Self

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
        self.domain = domain
        self.description = description
        self.dkim_v1 = dkim_v1
        self.google_site_verification = google_site_verification

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        return cls(
            d["id"],
            d["domain"],
            d["description"],
            [DKIMv1.from_dict(i) for i in d.get("dkim_v1", list())],
            d.get("google_site_verification", None),
        )

    def __str__(self) -> str:
        return self.domain

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, domain={self.domain})"


Domains = dict[DomainID, Domain]
