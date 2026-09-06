"""
tests/infralib/config/test_domain -- Domain Tests
=================================================

This file contains code to test infralib domains.
"""

import pytest

from infralib.config.domain import Domain


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
                    "test1_verification",
                ),
                "test1.example.com",
            ),
            (
                Domain(
                    "test2",
                    "test2.example.net",
                    "Second test case",
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
                    "test1_verification",
                ),
                "Domain(id=test1, domain=test1.example.com)",
            ),
            (
                Domain(
                    "test2",
                    "test2.example.net",
                    "Second test case",
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
