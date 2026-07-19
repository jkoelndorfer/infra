"""
infralib/config/notification -- Notification Configuration
==========================================================

This file defines data types for notification channels.
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Self

from ..error import InvalidConfigurationError


class NotificationCategory(StrEnum):
    """
    Enum describing the types of notifications that are sent.
    """

    # Notifications for cloud provider spending.
    CLOUD_BILLING = "cloud-billing"


class NotificationChannel(ABC):
    """
    Abstract class representing a notification channel.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        A human-readable name for the notification.
        """

    @property
    @abstractmethod
    def category(self) -> NotificationCategory:
        """
        What sort of notifications are sent over this channel.
        """

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NotificationChannel:
        chan_type = d["type"]
        match chan_type:
            case "email":
                return EmailChannel.from_dict(d)
            case _:
                raise InvalidConfigurationError(
                    "unknown notification channel type '{chan_type}'"
                )


class EmailChannel(NotificationChannel):
    """
    Channel for notifying via email.
    """

    def __init__(self, name: str, category: NotificationCategory, email: str) -> None:
        self._name = name
        self._category = category
        self.email = email

    @property
    def category(self) -> NotificationCategory:
        return self._category

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """
        Constructs an EmailChannel from a dictionary.
        """
        return cls(d["name"], NotificationCategory(d["category"]), d["email"])


NotificationChannels = list[NotificationChannel]
