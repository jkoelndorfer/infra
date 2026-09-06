"""
tests/infralib/config/test_domain -- Domain Tests
=================================================

This file contains code to test infralib domains.
"""

import pytest

from infralib.config.domain import DKIMv1, Domain


class TestDomain:
    """
    Contains tests for the Domain class.
    """

    @pytest.mark.parametrize(
        "domain, expected_str",
        [
            (
                Domain(
                    "test1",
                    "test1.example.com",
                    "First test case",
                    [],
                    "test1_verification",
                ),
                "test1.example.com",
            ),
            (
                Domain(
                    "test2",
                    "test2.example.net",
                    "Second test case",
                    [],
                    "test2_verification",
                ),
                "test2.example.net",
            ),
        ],
    )
    def test_str(self, domain: Domain, expected_str: str) -> None:
        """
        Tests that str(Domain) returns the expected value.
        """
        assert str(domain) == expected_str

    @pytest.mark.parametrize(
        "domain, expected_repr",
        [
            (
                Domain(
                    "test1",
                    "test1.example.com",
                    "First test case",
                    [],
                    "test1_verification",
                ),
                "Domain(id=test1, domain=test1.example.com)",
            ),
            (
                Domain(
                    "test2",
                    "test2.example.net",
                    "Second test case",
                    [],
                    "test2_verification",
                ),
                "Domain(id=test2, domain=test2.example.net)",
            ),
        ],
    )
    def test_repr(self, domain: Domain, expected_repr: str) -> None:
        """
        Tests that repr(Domain) returns the expected value.
        """
        assert repr(domain) == expected_repr


class TestDKIMv1:
    """
    Contains tests for the DKIMv1 class.
    """

    def test_from_dict_invalid_key_type_raises_error(self) -> None:
        """
        Tests that from_dict() raises an error when the provided key_type
        is not valid.
        """
        with pytest.raises(ValueError):
            DKIMv1.from_dict(
                {
                    "selector": "test",
                    "key_type": "not.valid",
                    "public_key": "pubkey",
                }
            )

    @pytest.mark.parametrize(
        "dkim, expected_str",
        [
            (
                DKIMv1(selector="test", key_type="rsa", public_key="pubkey1"),
                "v=DKIM1; k=rsa; p=pubkey1",
            ),
            (
                DKIMv1(selector="test", key_type="ed25519", public_key="pubkey2"),
                "v=DKIM1; k=ed25519; p=pubkey2",
            ),
        ],
    )
    def test_str(self, dkim: DKIMv1, expected_str: str) -> None:
        """
        Tests that __str__() returns the expected DKIM TXT record value.
        """
        assert str(dkim) == expected_str
