"""
Email the XLSX via SMTP. All settings come from environment variables; no
address or credential is hard-coded. Returns a status string instead of
raising, so a failed email never loses a saved submission.

  AUDIT_EMAIL_TO     comma-separated recipients (required to send)
  SMTP_HOST          e.g. smtp.office365.com (required to send)
  SMTP_PORT          default 587
  SMTP_USER          login user (optional if the relay needs no auth)
  SMTP_PASSWORD      login password / app password
  SMTP_FROM          sender address (defaults to SMTP_USER)
  SMTP_SECURITY      starttls (default) | ssl | none
"""

import os
import smtplib
import ssl
from email.message import EmailMessage

REQUIRED = ("AUDIT_EMAIL_TO", "SMTP_HOST")


def email_configured() -> tuple[bool, list[str]]:
    missing = [k for k in REQUIRED if not os.environ.get(k, "").strip()]
    if not (os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER")):
        missing.append("SMTP_FROM or SMTP_USER")
    return (not missing, missing)


def send_xlsx(record: dict, xlsx_bytes: bytes, filename: str) -> tuple[bool, str]:
    ok, missing = email_configured()
    if not ok:
        return False, "not sent: email not configured (missing " + ", ".join(missing) + ")"

    recipients = [a.strip() for a in os.environ["AUDIT_EMAIL_TO"].split(",") if a.strip()]
    sender = os.environ.get("SMTP_FROM") or os.environ["SMTP_USER"]
    msg = EmailMessage()
    msg["Subject"] = (f"Daily Report & Dashboard Discovery - {record['submission_id']} "
                      f"rev {record['revision']}")
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        "A daily report & dashboard discovery form was submitted.\n\n"
        f"Submission ID: {record['submission_id']}\n"
        f"Revision: {record['revision']}\n"
        f"Submitter: {record['submitter']} ({record.get('submitter_role') or '-'})\n"
        f"Submitted (UTC): {record['submitted_at_utc']}\n\n"
        "The XLSX is attached. This questionnaire covers processes only and "
        "contains no player-level medical data.\n")
    msg.add_attachment(xlsx_bytes, maintype="application",
                       subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       filename=filename)

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT") or 587)
    security = os.environ.get("SMTP_SECURITY", "starttls").lower()
    user, password = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    try:
        ctx = ssl.create_default_context()
        if security == "ssl":
            server = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
        with server:
            if security == "starttls":
                server.starttls(context=ctx)
            if user and password:
                server.login(user, password)
            server.send_message(msg)
    except Exception as exc:  # noqa: BLE001 - report any SMTP/network failure as status
        return False, f"failed: {type(exc).__name__}: {exc}"[:450]
    return True, f"sent to {len(recipients)} recipient(s)"
