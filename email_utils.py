"""
Sends the developer outreach message by real email, using Gmail SMTP.

Needs two environment variables set on Render:
  SMTP_EMAIL    - your Gmail address, e.g. openstore.team@gmail.com
  SMTP_PASSWORD - a Gmail "App Password" (NOT your normal Gmail password)

How to get a Gmail App Password:
  1. Turn on 2-Step Verification on the Gmail account (Google Account -> Security)
  2. Go to https://myaccount.google.com/apppasswords
  3. Create one for "Mail" -> copy the 16-character password
  4. Put that in Render's SMTP_PASSWORD env var (not your real Gmail password)
"""

import os
import smtplib
from email.mime.text import MIMEText

SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def generate_developer_message(developer_name: str, app_name: str) -> str:
    return (
        "Hello Developer,\n\n"
        "We are building OPEN STORE, an independent application marketplace.\n\n"
        f"NOVENTIX DEVELOPER discovered your application and would like to "
        f"make information about your application available on OPEN STORE.\n\n"
        f"Developer:\n{developer_name}\n\n"
        f"Application:\n{app_name}\n\n"
        "If you are the rights holder and would like your application "
        "distributed through OPEN STORE, please contact us or submit the "
        "application through our Developer Portal.\n\n"
        "If you do not want your application associated with OPEN STORE, "
        "please contact our support team and we will review your request.\n\n"
        "Thank you,\n"
        "OPEN STORE Team\n"
        "Powered by NOVENTIX DEVELOPER"
    )


def send_developer_email(to_email: str, developer_name: str, app_name: str) -> bool:
    """Returns True if the email was sent, False if it failed (bad address,
    no credentials configured, connection error, etc.) — never raises, so
    a bad send just becomes a normal MESSAGE_UNDELIVERABLE status."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False

    body = generate_developer_message(developer_name, app_name)
    msg = MIMEText(body)
    msg["Subject"] = f"Your application on OPEN STORE — {app_name}"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"EMAIL SEND FAILED: {e}")
        return False
