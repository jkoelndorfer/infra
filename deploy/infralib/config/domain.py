"""
infralib/config/domain -- Domain Configuration
==============================================

This file defines data types for domain configuration.
"""

from typing import Self

DomainID = str


class Domain:
    """
    Configuration representing a DNS domain.
    """

    def __init__(self, id: DomainID, domain: str, description: str) -> None:
        self.id = id
        self.domain = domain
        self.description = description

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Self:
        return cls(
            d["id"],
            d["domain"],
            d["description"],
        )

    def __str__(self) -> str:
        return self.domain

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, domain={self.domain})"


Domains = dict[DomainID, Domain]
