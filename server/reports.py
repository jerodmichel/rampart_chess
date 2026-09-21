"""Player reports - "this player/profile/message is abusive" - for a human
(the owner) to review. Nothing here acts automatically; see
admin_moderation.py for the tools that do (suspend, clear a profile).

  reports/{report_id} -> {
      reporter_uid, reporter_username, target_uid, target_username,
      kind,          # 'profile' | 'chat' | 'dm' | 'other'
      reason,        # one of REASONS
      details,       # free text from the reporter, <= MAX_DETAILS
      game_id,       # chat reports only
      excerpt,       # [{text, timestamp}] - the reported player's recent
                     # messages, copied at report time so they can't be
                     # edited/deleted away before review (chat/dm only)
      profile_snapshot,  # {bio} at report time (profile only)
      created_at, status,   # 'open' | 'resolved'
      resolved_at, resolution_note  (once resolved)
  }
  reports_by_reporter/{uid}/{report_id} -> created_at   # index nodes: the
  reports_by_target/{uid}/{report_id}   -> True         # daily cap + account
      deletion need "this account's reports" - kept as plain nodes read
      directly (never order_by_child), because Realtime Database refuses a
      query on any path without a ".indexOn" rule pasted into the Firebase
      console by hand (which friend_requests/challenges have, and reports
      deliberately doesn't need).

Kept after review (that's their point), but redacted if either account is
later deleted - see anonymize_for_deleted_user.
"""

import time

from fastapi import HTTPException
from firebase_admin import db

import accounts
import messages

KINDS = ("profile", "chat", "dm", "other")
REASONS = ("harassment", "hate", "spam", "inappropriate_image", "cheating", "other")
MAX_DETAILS = 500
MAX_EXCERPT_MESSAGES = 10
MAX_REPORTS_PER_DAY = 10   # per reporter - stops one account flooding the inbox
DELETED = "Deleted user"


def _recent_messages_by(entries: dict, author_uid: str, uid_field: str) -> list:
    rows = [v for v in entries.values() if isinstance(v, dict) and v.get(uid_field) == author_uid]
    rows.sort(key=lambda m: m.get("timestamp") or 0)
    return [{"text": (m.get("text") or "")[:500], "timestamp": m.get("timestamp")}
            for m in rows[-MAX_EXCERPT_MESSAGES:]]


def submit(reporter_uid: str, reporter_username: str, target_username: str, kind: str,
           reason: str, details: str = "", verified_game_id: str = None) -> dict:
    """`verified_game_id` must already have been checked by the caller
    (app.py) to be a game the reporter took part in - this module only
    reads the chat, it doesn't know about game sessions."""
    if kind not in KINDS:
        raise HTTPException(status_code=400, detail=f"kind must be one of {KINDS}")
    if reason not in REASONS:
        raise HTTPException(status_code=400, detail=f"reason must be one of {REASONS}")
    details = (details or "").strip()
    if len(details) > MAX_DETAILS:
        raise HTTPException(status_code=400, detail=f"details can't exceed {MAX_DETAILS} characters")

    target_uid = accounts.lookup_uid(target_username)
    if target_uid == reporter_uid:
        raise HTTPException(status_code=400, detail="you can't report yourself")

    # Simple per-account daily cap (reports are rare, so the whole index row is tiny).
    mine = db.reference(f"reports_by_reporter/{reporter_uid}").get() or {}
    cutoff = int(time.time() * 1000) - 24 * 60 * 60 * 1000
    if sum(1 for created in mine.values() if (created or 0) > cutoff) >= MAX_REPORTS_PER_DAY:
        raise HTTPException(status_code=429, detail="you've sent a lot of reports today - please try again tomorrow")

    target_username = db.reference(f"users/{target_uid}/username").get() or target_username
    record = {
        "reporter_uid": reporter_uid,
        "reporter_username": reporter_username,
        "target_uid": target_uid,
        "target_username": target_username,
        "kind": kind,
        "reason": reason,
        "details": details,
        "status": "open",
        "created_at": {".sv": "timestamp"},
    }
    if kind == "chat" and verified_game_id:
        record["game_id"] = verified_game_id
        record["excerpt"] = _recent_messages_by(
            db.reference(f"game_chat/{verified_game_id}").get() or {}, target_uid, "uid")
    elif kind == "dm":
        thread_id = messages._thread_id(reporter_uid, target_uid)
        record["excerpt"] = _recent_messages_by(
            db.reference(f"dm_threads/{thread_id}/messages").get() or {}, target_uid, "from_uid")
    elif kind == "profile":
        record["profile_snapshot"] = {"bio": db.reference(f"users/{target_uid}/bio").get() or ""}

    ref = db.reference("reports").push(record)
    stored = ref.get()
    db.reference(f"reports_by_reporter/{reporter_uid}/{ref.key}").set(stored["created_at"])
    db.reference(f"reports_by_target/{target_uid}/{ref.key}").set(True)
    return {"report_id": ref.key, **stored}


def anonymize_for_deleted_user(uid: str) -> None:
    """Account deletion. Reports stay (they document moderation decisions and
    the OTHER person's complaint), but nothing may link back to a deleted
    account: their identity is blanked, and if they were the one reported,
    the copied messages/bio snapshot are dropped too."""
    for index, field, name_field, content in (
            ("reports_by_reporter", "reporter_uid", "reporter_username", False),
            ("reports_by_target", "target_uid", "target_username", True)):
        for report_id in (db.reference(f"{index}/{uid}").get() or {}):
            update = {field: None, name_field: DELETED}
            if content:
                update.update({"excerpt": None, "profile_snapshot": None, "details": None})
            db.reference(f"reports/{report_id}").update(update)
        db.reference(f"{index}/{uid}").delete()
