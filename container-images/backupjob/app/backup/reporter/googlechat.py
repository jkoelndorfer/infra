"""
backup.reporter.googlechat
==========================

Provides a backup reporter that submits reports to Google Chat via webhook.

See https://developers.google.com/workspace/chat/quickstart/webhooks.
"""

from datetime import datetime, timedelta
from http import HTTPStatus
from io import StringIO
from time import sleep
from typing import Any, Optional

from requests import Response, Session

from ..report import BackupReport, BackupReportField, BackupReportFieldAnnotation as A


class GoogleChatWebhookResponse:
    """
    Object representing a response to a Google Chat webhook POST request.
    """

    def __init__(self, response: Response) -> None:
        self.response = response


class GoogleChatReportRenderer:
    """
    Renders backup reports into Google Chat messages.
    """

    def __init__(self) -> None:
        # The maximum line length for non-multiline fields and data before a newline is added.
        #
        # This value was chosen based on how many characters fit in a single line on a phone.
        self.max_line_length = 32

        self.annotation_emoji = {
            A.OK.value: "✅",
            A.WARNING.value: "⚠️",
            A.ERROR.value: "🚨",
            A.ERROR_UNKNOWN.value: "❓",
        }

    def field_emoji(
        self, field: BackupReportField, before: str = "", after: str = ""
    ) -> str:
        """
        Returns the emoji corresponding to the backup field's annotation with
        optional characters before or after.

        If there is no annotation or corresponding emoji, returns an empty string.
        """
        a = field.annotation

        if a is None:
            return ""

        emoji = self.annotation_emoji.get(a.value, None)

        if emoji is None:
            return ""

        return f"{before}{emoji}{after}"

    def render_field(self, field: BackupReportField) -> str:
        """
        Renders the given field to a string based on its data and annotation.
        """
        if isinstance(field.data, bool):
            return self.render_bool_field(field)
        elif field.annotation == A.MULTILINE_TEXT:
            return self.render_multiline_text_field(field)
        else:
            return self.render_text_field(field)

    def render_bool_field(self, field: BackupReportField[bool]) -> str:
        """
        Renders a boolean field to a string based on its data and annotation.
        """
        m = {
            True: "yes",
            False: "no",
        }
        return f"*{field.label}* {m[field.data]}{self.field_emoji(field, before=' ')}"

    def render_multiline_text_field(self, field: BackupReportField) -> str:
        """
        Renders a multiline text field to a string based on its data and annotation.
        """
        return f"*{field.label}*\n{field.data}"

    def render_text_field(self, field: BackupReportField) -> str:
        """
        Renders a text field to a string based on its data and annotation.
        """
        return f"*{field.label}* {str(field.data)}{self.field_emoji(field, before=' ')}"

    def render_report(self, backup_report: BackupReport) -> str:
        """
        Renders a backup report into a Google Chat message.
        """
        sio = StringIO()
        if backup_report.successful:
            report_emoji = self.annotation_emoji[A.OK.value]
        else:
            report_emoji = self.annotation_emoji[A.ERROR.value]

        sio.write(f"*{backup_report.name}* {report_emoji}\n")

        current_line_length = 0
        field_padding = "  "
        current_padding = ""
        newline = False
        for f in backup_report.fields:
            fstr = self.render_field(f)

            if current_line_length == 0:
                # If the current line has nothing on it, we never write a newline.
                # The field label and data is simply longer than the maximum permitted.
                newline = False
                current_padding = ""
            elif f.annotation == A.MULTILINE_TEXT:
                # If a field is a multiline text field, we always put the label on its
                # own line. It reads more cleanly.
                newline = True
                current_padding = ""
            elif (
                current_line_length + len(field_padding) + len(fstr) - 2
                > self.max_line_length
            ):
                # If the additional field label and data exceed the maximum, put the
                # field on a new line with no padding.
                #
                # Note: the -2 in the calculation above accounts for the fact that
                # field labels are *bolded*. The asterisks aren't printed.
                newline = True
                current_padding = ""
            else:
                # Otherwise, we can fit this additional field on the same line.
                newline = False
                current_padding = field_padding

            if newline:
                sio.write("\n")
                current_line_length = 0

            sio.write(current_padding)
            sio.write(fstr)

            current_line_length += len(current_padding) + len(fstr)

        text = sio.getvalue()
        sio.close()
        return text


class GoogleChatBackupReporter:
    """
    Backup reporter that submits reports to Google Chat via a webhook.
    """

    def __init__(
        self, webhook_url: str, renderer: GoogleChatReportRenderer, session: Session
    ) -> None:
        self.webhook_url = webhook_url
        self.renderer = renderer
        self.session = session

        # The number of seconds between messages posted to Google Chat. This helps avoid us
        # overrunning the rate limit.
        #
        # https://developers.google.com/workspace/chat/quickstart/webhooks#limits
        self.seconds_between_messages = 2
        self._last_msg_put = datetime.now() - timedelta(
            seconds=self.seconds_between_messages * 2
        )
        self.sleep = sleep

        self._headers = {
            "Content-Type": "application/json; charset=UTF-8",
        }

        self._params = {
            # This query parameter will enable posting threaded messages using threadKey.
            "messageReplyOption": "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD",
        }

    def put_message(
        self, text: str, thread_key: Optional[str] = None
    ) -> GoogleChatWebhookResponse:
        """
        Submits the given message to Google Chat.
        """
        payload: dict[str, Any] = {"text": text}

        if thread_key is not None:
            payload["thread"] = {"threadKey": thread_key}

        tries = 0

        self.wait_for_msg_put()

        while True:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                headers=self._headers,
                params=self._params,
            )

            match response.status_code:
                case HTTPStatus.TOO_MANY_REQUESTS:
                    # If we're 429'd, retry. Sleep a little extra, too.
                    self.sleep(self.seconds_between_messages)

                case _:
                    # On success (or any unhandled failure) abort.
                    break

            if tries >= 3:
                break

            tries += 1
            self.sleep(self.seconds_between_messages)

        self._last_msg_put = datetime.now()
        return GoogleChatWebhookResponse(response)

    def report(self, backup_report: BackupReport) -> list[GoogleChatWebhookResponse]:
        """
        Submits a backup report and all its subreports to Google Chat.
        """
        responses: list[GoogleChatWebhookResponse] = list()
        now_s = datetime.now().strftime("%Y-%m-%dT%H:%M")
        thread_key = self.thread_keyize(f"{backup_report.name}@{now_s}")

        for r in backup_report.all_reports():
            if r.omittable:
                continue
            response = self.report_one(r, thread_key=thread_key)
            responses.append(response)

        return responses

    def report_one(
        self, backup_report: BackupReport, thread_key: Optional[str] = None
    ) -> GoogleChatWebhookResponse:
        """
        Submits a single backup report to Google Chat.
        """
        text = self.renderer.render_report(backup_report)
        return self.put_message(text, thread_key)

    @classmethod
    def thread_keyize(cls, s: str) -> str:
        """
        Returns s with alterations such that it is suitable for use as a Google Chat thread key.
        """
        return s.replace(" ", "-")

    def wait_for_msg_put(self) -> None:
        """
        Waits until a message can be put.
        """
        msg_is_puttable = self._last_msg_put + timedelta(
            seconds=self.seconds_between_messages
        )

        while datetime.now() < msg_is_puttable:
            self.sleep(0.1)
