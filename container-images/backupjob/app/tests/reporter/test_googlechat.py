"""
Tests Google Chat reporter functionality.
"""

from datetime import datetime, timedelta
from http import HTTPStatus
from os import environ
from textwrap import dedent
from unittest.mock import create_autospec, MagicMock
from typing import cast

import pytest
from requests import Response, Session

from backup.report import (
    BackupReport,
    BackupReportField as F,
    BackupReportFieldAnnotation as A,
)
from backup.reporter.googlechat import (
    GoogleChatBackupReporter,
    GoogleChatReportRenderer,
)


@pytest.fixture
def session_mock() -> Session:
    """
    A requests.Session mock.
    """
    return create_autospec(Session)


@pytest.fixture
def single_backup_report() -> BackupReport:
    """
    A single backup report with no subreports.
    """
    r = BackupReport("Test Single Report")
    r.successful = True
    r.new_field("Init OK", True, lambda x: A.OK if x else A.ERROR)
    r.new_field("New Repo", True, lambda x: A.OK if not x else A.WARNING)
    r.new_field("Src", "/data", lambda x: None)
    r.new_field("Dest", "/dest", lambda x: None)

    return r


@pytest.fixture
def multi_backup_report() -> BackupReport:
    """
    A backup report with multiple subreports.
    """
    r1 = BackupReport("Test Multi Report")
    r1.new_field("Init OK", True, lambda x: A.OK if x else A.ERROR)
    r1.new_field("New Repo", False, lambda x: A.OK if not x else A.WARNING)
    r1_backup_start = r1.new_field("Backup Start", datetime.now(), lambda x: None)
    r1.successful = True

    r2 = r1.new_subreport("Backup Sub1")
    r2_backup_start = r2.new_field(
        "Backup Start", r1_backup_start.data + timedelta(seconds=2), lambda x: None
    )
    r2_backup_end = r2.new_field(
        "Backup End", r2_backup_start.data + timedelta(minutes=1), lambda x: None
    )
    r2.new_field("New Files", 1024, lambda x: None)
    r2.successful = True

    r3 = r1.new_subreport("Backup Sub2")
    r3_backup_start = r3.new_field(
        "Backup Start", r2_backup_end.data + timedelta(minutes=1), lambda x: None
    )
    r3_backup_end = r3.new_field(
        "Backup End", r3_backup_start.data + timedelta(minutes=10), lambda x: None
    )
    r3.new_field("New Files", 2048, lambda x: None)
    r3.successful = True

    r1.new_field(
        "Backup End", r3_backup_end.data + timedelta(seconds=10), lambda x: None
    )

    return r1


@pytest.fixture(scope="session")
def renderer() -> GoogleChatReportRenderer:
    """
    A GoogleChatReportRenderer object.
    """
    return GoogleChatReportRenderer()


@pytest.fixture
def google_chat_webhook_mock_url() -> str:
    """
    Mock webhook URI for Google Chat reporting.
    """
    return (
        "https://chat.googleapis.local"
        "/v1/spaces/xxxxxxxxxxx/messages"
        "?key=xxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx&token=xxxxxxxxxxxxxx-xxxxxx_xxxxxxxxxxxxxxxxxxxxx"
    )


@pytest.fixture
def google_chat_backup_reporter_mock(
    google_chat_webhook_mock_url: str,
    renderer: GoogleChatReportRenderer,
    session_mock: Session,
) -> GoogleChatBackupReporter:
    """
    GoogleChatReporter with a mock requests.Session object.
    """
    return GoogleChatBackupReporter(
        google_chat_webhook_mock_url, renderer, session_mock
    )


@pytest.fixture(scope="session")
def google_chat_webhook_url() -> str:
    """
    Live webhook URI for Google Chat reporting.
    """
    url = environ.get("GOOGLE_CHAT_WEBHOOK_URL", None)
    if url is None or url == "":
        pytest.skip(
            reason="GOOGLE_CHAT_WEBHOOK_URL must be set to perform live Google Chat webhook tests"
        )
    return url


@pytest.fixture(scope="session")
def google_chat_backup_reporter(
    google_chat_webhook_url: str, renderer: GoogleChatReportRenderer
) -> GoogleChatBackupReporter:
    """
    GoogleChatReporter with a live requests.Session object.

    This fixture is session-scoped to ensure rate limits are respected.
    """
    return GoogleChatBackupReporter(google_chat_webhook_url, renderer, Session())


class TestGoogleChatReportRenderer:
    """
    Tests the GoogleChatReportRenderer class.
    """

    @pytest.mark.parametrize(
        "field, before, after, expected",
        [
            (F("n/a", True, lambda x: A.OK if x else A.ERROR), " ", " ", " ✅ "),
            (F("n/a", True, lambda x: A.OK if x else A.ERROR), "  ", "  ", "  ✅  "),
            (F("n/a", True, lambda x: A.MULTILINE_TEXT), "  ", "  ", ""),
            (F("n/a", True, lambda x: None), "  ", "  ", ""),
            (F("n/a", False, lambda x: A.OK if x else A.ERROR), " ", " ", " 🚨 "),
        ],
    )
    def test_field_emoji(
        self,
        renderer: GoogleChatReportRenderer,
        field: F,
        before: str,
        after: str,
        expected: str,
    ) -> None:
        """
        Tests the field_emoji method.
        """
        assert renderer.field_emoji(field, before, after) == expected

    @pytest.mark.parametrize(
        "field, expected",
        [
            (F("Init OK", True, lambda x: A.OK if x else A.ERROR), "*Init OK* yes ✅"),
            (
                F("Init OK", False, lambda x: A.OK if x else A.ERROR),
                "*Init OK* no 🚨",
            ),
            (
                F("New Repository", True, lambda x: A.OK if not x else A.WARNING),
                "*New Repository* yes ⚠️",
            ),
            (
                F("Snapshot Taken", True, lambda x: None),
                "*Snapshot Taken* yes",
            ),
            (
                F("New Files", 128, lambda x: A.OK if x > 0 else A.WARNING),
                "*New Files* 128 ✅",
            ),
            (
                F(
                    "Error",
                    "Traceback (most recent call last):\n...\nKeyError: 'k'",
                    lambda x: A.MULTILINE_TEXT,
                ),
                "*Error*\nTraceback (most recent call last):\n...\nKeyError: 'k'",
            ),
        ],
    )
    def test_render_field(
        self,
        renderer: GoogleChatReportRenderer,
        field: F,
        expected: str,
    ) -> None:
        """
        Tests the render_field method.
        """

        assert renderer.render_field(field) == expected

    def test_render_comprehensive_report(
        self, renderer: GoogleChatReportRenderer
    ) -> None:
        """
        Tests the render_report method using a comprehensive backup report.
        """
        report = BackupReport("Test Single Report")
        report.successful = True
        report.new_field("Init OK", True, lambda x: A.OK if x else A.ERROR)
        report.new_field("New Repo", False, lambda x: A.OK if not x else A.WARNING)
        report.new_field("Src", "/data", lambda x: None)
        report.new_field("Dest", "/dest", lambda x: None)
        report.new_field("New Files", 32, lambda x: None)
        report.new_field("Data Added", 2048, lambda x: None)
        report.new_field(
            "Output", "Backup run successful!\nBon voyage!", lambda x: A.MULTILINE_TEXT
        )

        expected = dedent("""
            *Test Single Report* ✅
            *Init OK* yes ✅  *New Repo* no ✅
            *Src* /data  *Dest* /dest
            *New Files* 32  *Data Added* 2048
            *Output*
            Backup run successful!
            Bon voyage!
        """).strip()

        assert renderer.render_report(report) == expected


class TestGoogleChatBackupReporterMockSession:
    """
    Tests the GoogleChatBackupReporter with a mock requests.Session.
    """

    def test_report(
        self,
        google_chat_backup_reporter_mock: GoogleChatBackupReporter,
        google_chat_webhook_mock_url: str,
        renderer: GoogleChatReportRenderer,
        single_backup_report: BackupReport,
    ) -> None:
        """
        Tests the report method.
        """
        post = cast(MagicMock, google_chat_backup_reporter_mock.session.post)
        google_chat_backup_reporter_mock.report(single_backup_report)

        assert post.call_count == 1

        call = post.call_args_list[0]
        args = call[0]
        kwargs = call[1]

        assert args[0] == google_chat_webhook_mock_url
        assert kwargs["json"]["text"] == renderer.render_report(single_backup_report)
        assert isinstance(kwargs["json"]["thread"]["threadKey"], str)
        assert kwargs["headers"] == {"Content-Type": "application/json; charset=UTF-8"}
        assert (
            kwargs["params"]["messageReplyOption"]
            == "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"
        )

    def test_report_429_retry(
        self,
        google_chat_backup_reporter_mock: GoogleChatBackupReporter,
        single_backup_report: BackupReport,
    ) -> None:
        """
        Tests that the report method retries on HTTP 429 (too many requests).
        """
        count_429 = 0

        def post_429(*args, **kwargs):
            nonlocal count_429
            r = Response()
            if count_429 >= 2:
                r.status_code = HTTPStatus.OK
            else:
                count_429 += 1
                r.status_code = HTTPStatus.TOO_MANY_REQUESTS
            return r

        post = cast(MagicMock, google_chat_backup_reporter_mock.session.post)
        post.side_effect = post_429

        google_chat_backup_reporter_mock.seconds_between_messages = 0

        google_chat_backup_reporter_mock.report(single_backup_report)

        assert post.call_count == 3

    def test_report_429_gives_up(
        self,
        google_chat_backup_reporter_mock: GoogleChatBackupReporter,
        single_backup_report: BackupReport,
    ) -> None:
        """
        Tests that the report method gives up completely after too many 429 responses.
        """

        def post_429(*args, **kwargs):
            r = Response()
            r.status_code = HTTPStatus.TOO_MANY_REQUESTS
            return r

        post = cast(MagicMock, google_chat_backup_reporter_mock.session.post)
        post.side_effect = post_429

        google_chat_backup_reporter_mock.seconds_between_messages = 0

        google_chat_backup_reporter_mock.report(single_backup_report)

        assert post.call_count == 4

    @pytest.mark.slow
    def test_wait_for_msg_put(
        self, google_chat_backup_reporter_mock: GoogleChatBackupReporter
    ) -> None:
        """
        Tests that put_message sleeps between message puts.
        """

        google_chat_backup_reporter_mock.put_message("test message 1")
        before_msg_2 = datetime.now()
        google_chat_backup_reporter_mock.put_message("test message 2")
        after_msg_2 = datetime.now()

        assert (after_msg_2 - before_msg_2) >= timedelta(
            seconds=google_chat_backup_reporter_mock.seconds_between_messages
        )


@pytest.mark.live
class TestGoogleChatReporterIntegration:
    """
    Tests the GoogleChatReporter with a live requests.Session and Google Chat webhook endpoint.
    """

    def test_single_report(
        self,
        google_chat_backup_reporter: GoogleChatBackupReporter,
        single_backup_report: BackupReport,
    ) -> None:
        """
        Tests the report method against the Google Chat webhook endpoint.
        """

        google_chat_backup_reporter.report(single_backup_report)

    def test_report_with_subreports(
        self,
        google_chat_backup_reporter: GoogleChatBackupReporter,
        multi_backup_report: BackupReport,
    ) -> None:
        """
        Tests the report method against the Google Chat webhook endpoint where
        the report has multiple subreports.
        """
        google_chat_backup_reporter.report(multi_backup_report)
