"""Notifies a user about something (so far: being challenged) through a
channel that reaches them even when they're not actively on the site -
important while traffic is still low and there's no native app to lean on
for push. Email today (via Resend); Web Push is a planned follow-up that
will live in this same module (see the approved plan) rather than a
redesign, since both start from "look up how to reach this uid."

Config is env vars, matching the FIREBASE_CREDENTIALS_PATH/
FIREBASE_DATABASE_URL pattern already used in firebase_auth.py:

  RESEND_API_KEY      - from the user's Resend account
  RESEND_FROM_ADDRESS - the verified sending address/domain in Resend
  SITE_BASE_URL        - used to build the link in the email body

None of these are committed - same rule as serviceAccountKey.json.
"""

import html as html_lib
import logging
import os
from typing import Optional

import resend
from firebase_admin import auth as firebase_auth_sdk

logger = logging.getLogger(__name__)

resend.api_key = os.environ.get("RESEND_API_KEY")
_FROM_ADDRESS = os.environ.get("RESEND_FROM_ADDRESS")
_SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "http://localhost:5500")


def notify_user(uid: str, subject: str, body_text: str, body_html: Optional[str] = None) -> None:
    """Best-effort: never raises. A notification failing must not break
    whatever action triggered it (e.g. creating a challenge) - same
    "decorative, not load-bearing" reasoning as header.js's own
    renderHeaderTrophies on the client side. `body_html` is optional so a
    future caller can still send a plain-text-only notification; every
    caller should still pass body_text as a fallback for clients that
    don't render HTML mail.
    """
    if not resend.api_key or not _FROM_ADDRESS:
        logger.warning("notify_user skipped for %s: RESEND_API_KEY/RESEND_FROM_ADDRESS not configured", uid)
        return
    try:
        email = firebase_auth_sdk.get_user(uid).email
    except Exception as e:
        logger.warning("notify_user: couldn't look up email for %s: %s", uid, e)
        return
    if not email:
        return
    payload = {
        "from": _FROM_ADDRESS,
        "to": [email],
        "subject": subject,
        "text": body_text,
    }
    if body_html:
        payload["html"] = body_html
    try:
        resend.Emails.send(payload)
    except Exception as e:
        logger.warning("notify_user: email send failed for %s: %s", uid, e)


# Matches the friendly labels already used client-side for the same raw
# time_control keys (web/js/profile.js's TIME_CONTROL_LABELS) - kept as its
# own copy rather than a shared source of truth, since one's Python and one's
# JS and there's no existing shared-constants mechanism between them.
_TIME_CONTROL_LABELS = {
    "30min": "30-minute",
    "1hour": "1-hour",
    "1day_per_move": "day-per-move",
}


def _email_layout(heading: str, body_html_inner: str) -> str:
    """Shared chrome (light background, serif heading, accent button style)
    every notification email wraps its own content in - keeps a consistent
    RampartChess look without each notify_* function reimplementing it.
    Inline styles throughout, not a <style> block - many email clients
    strip <style> tags entirely, so inline is the only reliably safe way to
    style transactional email."""
    return f"""\
<div style="font-family: Georgia, 'Times New Roman', serif; max-width: 480px;
            margin: 0 auto; padding: 32px 24px; background: #ffffff; color: #222;">
  <h1 style="font-size: 20px; margin: 0 0 4px; color: #111;">RampartChess</h1>
  <hr style="border: none; border-top: 1px solid #ddd; margin: 12px 0 20px;">
  <p style="font-size: 16px; margin: 0 0 20px; line-height: 1.5;">{heading}</p>
  {body_html_inner}
</div>"""


def _button_html(url: str, label: str) -> str:
    safe_url = html_lib.escape(url, quote=True)
    return f"""\
  <p style="margin: 0 0 24px;">
    <a href="{safe_url}" style="display: inline-block; background: #9f2b68; color: #ffffff;
       padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold;
       font-size: 15px;">{html_lib.escape(label)}</a>
  </p>
  <p style="font-size: 13px; color: #777; margin: 0;">
    If the button doesn't work, copy this link into your browser:<br>
    <a href="{safe_url}" style="color: #9f2b68;">{safe_url}</a>
  </p>"""


def notify_challenge(to_uid: str, from_username: str, time_control: str) -> None:
    label = _TIME_CONTROL_LABELS.get(time_control, time_control)
    url = f"{_SITE_BASE_URL}/index.html"
    subject = f"{from_username} challenged you on RampartChess!"
    body_text = (
        f"{from_username} sent you a {label} challenge on RampartChess.\n\n"
        f"Accept it here: {url}"
    )
    heading = (
        f"<strong>{html_lib.escape(from_username)}</strong> challenged you to a "
        f"{html_lib.escape(label)} game."
    )
    body_html = _email_layout(heading, _button_html(url, "Accept the Challenge"))
    notify_user(to_uid, subject, body_text, body_html)
