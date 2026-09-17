"""
Sends the developer outreach message via Mailjet's HTTP email API.

Render blocks outbound SMTP traffic on all plans, so a direct email send
via smtplib always times out there — this uses a plain HTTPS API call
instead, which isn't blocked.

Needs three environment variables set on Render:
  MAILJET_API_KEY    - from Mailjet dashboard -> Account Settings -> API Key Management
  MAILJET_API_SECRET - the matching Secret Key from the same page
  SMTP_EMAIL          - the sender address, must be a verified sender in Mailjet

How to set up Mailjet (free, no credit card):
  1. Sign up at https://www.mailjet.com
  2. Go to Account Settings -> Sender addresses & domains -> Add a sender
     address, use your email, click the verification link Mailjet emails you
  3. Go to Account Settings -> API Key Management -> copy the API Key and
     Secret Key
  4. Put those in Render's MAILJET_API_KEY and MAILJET_API_SECRET env vars,
     and your verified email in SMTP_EMAIL
"""

import os
import requests
from requests.auth import HTTPBasicAuth

MAILJET_API_KEY = os.environ.get("MAILJET_API_KEY")
MAILJET_API_SECRET = os.environ.get("MAILJET_API_SECRET")
SMTP_EMAIL = os.environ.get("SMTP_EMAIL")


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
    """Returns True if Mailjet accepted the email, False otherwise — never
    raises, so a bad send just becomes a normal MESSAGE_UNDELIVERABLE
    status."""
    if not MAILJET_API_KEY or not MAILJET_API_SECRET or not SMTP_EMAIL:
        print("EMAIL SEND FAILED: MAILJET_API_KEY/SECRET or SMTP_EMAIL not set")
        return False

    body = generate_developer_message(developer_name, app_name)

    try:
        response = requests.post(
            "https://api.mailjet.com/v3.1/send",
            auth=HTTPBasicAuth(MAILJET_API_KEY, MAILJET_API_SECRET),
            json={
                "Messages": [
                    {
                        "From": {"Email": SMTP_EMAIL, "Name": "OPEN STORE Team"},
                        "To": [{"Email": to_email}],
                        "Subject": f"Your application on OPEN STORE — {app_name}",
                        "TextPart": body,
                    }
                ]
            },
            timeout=15,
        )
        if response.status_code == 200:
            return True
        print(f"EMAIL SEND FAILED: {response.status_code} {response.text}")
        return False
    except Exception as e:
        print(f"EMAIL SEND FAILED: {e}")
        return False
