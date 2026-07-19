"""
tests/infralib/pulumi/test_backend -- Pulumi Backend Tests
==========================================================

This file contains code to test Pulumi backend providers.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from infralib import (
    InfrastructureStack,
    LocalBackendProvider,
)
from infralib.error import InvalidLocalBackendError


class TestLocalBackendProvider:
    """
    Contains tests for the LocalBackendProvider class.
    """

    def test_missing_sentinel_file_raises_error(self) -> None:
        """
        Tests that attempting to instantiate a LocalBackendProvider raises an
        error if the sentinel file is missing.
        """
        with TemporaryDirectory(
            prefix="infralib-test-local-backend-", ignore_cleanup_errors=True
        ) as d:
            with pytest.raises(InvalidLocalBackendError):
                LocalBackendProvider(Path(d))

    def test_pulumi_url(
        self,
        local_backend_provider: LocalBackendProvider,
        local_backend_dir: Path,
        noop_infrastructure_stack: InfrastructureStack,
    ) -> None:
        """
        Tests that pulumi_url() returns the expected value.
        """
        expected = f"file://{local_backend_dir}"
        actual = local_backend_provider.pulumi_url(noop_infrastructure_stack)

        assert actual == expected
