"""
tests/infralib/config/test_domain -- Domain Tests
=================================================

This file contains code to test infralib domains.
"""

import pytest

from infralib import DeploymentTarget, Environment
from infralib.config.domain import DKIMv1, Domain


@pytest.fixture
def example_com_domain() -> Domain:
    return Domain(
        id="example",
        domain="example.com",
        description="Example Domain",
        dkim_v1=[],
        google_site_verification=None,
    )


class TestDomain:
    """
    Contains tests for the Domain class.
    """

    @pytest.mark.parametrize(
        "target, expected_domain",
        [
            (
                DeploymentTarget(Environment.PROD, None),
                "example.com",
            ),
            (
                DeploymentTarget(Environment.DEV, None),
                "dev.example.com",
            ),
            (
                DeploymentTarget(Environment.PROD, "europe-west-2"),
                "europe-west-2.example.com",
            ),
            (
                DeploymentTarget(Environment.DEV, "europe-west-2"),
                "europe-west-2.dev.example.com",
            ),
        ],
    )
    def test_domain_for(
        self,
        example_com_domain: Domain,
        target: DeploymentTarget,
        expected_domain: str,
    ) -> None:
        """
        Tests that domain_for returns the expected domain name.
        """
        assert example_com_domain.domain_for(target) == expected_domain

    @pytest.mark.parametrize(
        "target, expected_host",
        [
            (
                DeploymentTarget(Environment.PROD, None),
                "",
            ),
            (
                DeploymentTarget(Environment.DEV, None),
                "dev",
            ),
            (
                DeploymentTarget(Environment.PROD, "europe-west-2"),
                "europe-west-2",
            ),
            (
                DeploymentTarget(Environment.DEV, "europe-west-2"),
                "europe-west-2.dev",
            ),
        ],
    )
    def test_host_for(
        self,
        example_com_domain: Domain,
        target: DeploymentTarget,
        expected_host: str,
    ) -> None:
        """
        Tests that host_for returns the expected hostname.
        """
        assert example_com_domain.host_for(target) == expected_host

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
