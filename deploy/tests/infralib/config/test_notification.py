"""
tests/infralib/config/test_notification -- Notification Channel Tests
=====================================================================

This file contains code to test infralib notification channel configuration.
"""

import pytest

from infralib.error import InvalidConfigurationError
from infralib.config.notification import NotificationChannel


class TestNotificationChannel:
    """
    Contains tests for the NotificationChannel class.
    """

    def test_invalid_channel_type_raises_error(self) -> None:
        """
        Tests that NotificationChannel.from_dict() raises an error when the
        channel type is invalid.
        """
        invalid_channel_dict = {
            "name": "Channel With Invalid Type",
            "category": "testing",
            "type": "AnInvalidChannelType",
        }

        with pytest.raises(InvalidConfigurationError):
            NotificationChannel.from_dict(invalid_channel_dict)
