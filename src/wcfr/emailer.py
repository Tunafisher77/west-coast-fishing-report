from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_report(report_path: Path, subject: str) -> None:
    required = ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "REPORT_TO"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing email configuration: " + ", ".join(missing))

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.environ.get("REPORT_FROM", os.environ["SMTP_USERNAME"])
    message["To"] = os.environ["REPORT_TO"]
    message.set_content("This report requires an HTML-capable email client.")
    message.add_alternative(report_path.read_text(encoding="utf-8"), subtype="html")

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)
