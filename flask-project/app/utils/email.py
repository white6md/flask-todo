from __future__ import annotations

import logging
from typing import Iterable

from flask import current_app
from flask_mail import Message

from ..extensions import mail

logger = logging.getLogger(__name__)


def send_email(subject: str, recipients: Iterable[str], body: str, html: str | None = None) -> None:
    if not recipients:
        return

    if not current_app.config.get("MAIL_USERNAME"):
        logger.warning("MAIL_USERNAME is not configured; email will be logged only.")
        logger.info("Subject: %s\nRecipients: %s\nBody: %s", subject, ", ".join(recipients), body)
        return

    message = Message(subject=subject, recipients=list(recipients), body=body, html=html)
    mail.send(message)
