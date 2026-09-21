"""Direct messages between friends - private, one thread per friend pair -
backed by the same Realtime Database everything else uses:

  dm_threads/{thread_id}/messages/{message_id} -> {from_uid, text, timestamp}
  user_threads/{uid}/{thread_id} -> {other_uid, other_username, last_text,
                                      last_timestamp, unread}
      denormalized preview info, written to BOTH participants on every
      send - lets the inbox list every conversation with a snippet/time
      in one read instead of N+1 (one read per thread).
      `unread` is per participant: set True on the RECIPIENT's entry when a
      message arrives, False on the sender's, cleared by mark_read(). It
      drives the header notification bell. A thread from before this field
      existed has none, which reads as "not unread" - no flood of false
      alerts for old conversations.

thread_id is deterministic - the two uids sorted and joined - rather than
a pushed id, so "the conversation between A and B" needs no lookup step at
all and doubles as the authorization check (a uid is a participant iff it
appears in the thread_id). Firebase uids are plain alphanumeric (no RTDB
key-illegal characters), same reasoning accounts.py's username validation
already leans on.

Gated on friends.is_friend() - you can only message an accepted friend,
never an arbitrary player.
"""

from fastapi import HTTPException
from firebase_admin import db

import accounts
import blocks
import friends

MAX_MESSAGE_LENGTH = 500


def _thread_id(uid1: str, uid2: str) -> str:
    return "_".join(sorted([uid1, uid2]))


def _require_participant(thread_id: str, uid: str) -> None:
    if uid not in thread_id.split("_"):
        raise HTTPException(status_code=403, detail="you're not part of this conversation")


def send_message(from_uid: str, from_username: str, to_username: str, text: str) -> dict:
    to_uid = accounts.lookup_uid(to_username)
    blocks.require_can_interact(from_uid, to_uid, "message")
    if not friends.is_friend(from_uid, to_uid):
        raise HTTPException(status_code=403, detail="you can only message a friend")

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="message can't be empty")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"message can't exceed {MAX_MESSAGE_LENGTH} characters")

    thread_id = _thread_id(from_uid, to_uid)
    record = {"from_uid": from_uid, "text": text, "timestamp": {".sv": "timestamp"}}
    ref = db.reference(f"dm_threads/{thread_id}/messages").push(record)
    stored = ref.get()

    db.reference(f"user_threads/{from_uid}/{thread_id}").update({
        "other_uid": to_uid, "other_username": to_username,
        "last_text": text, "last_timestamp": stored["timestamp"],
        "unread": False,
    })
    db.reference(f"user_threads/{to_uid}/{thread_id}").update({
        "other_uid": from_uid, "other_username": from_username,
        "last_text": text, "last_timestamp": stored["timestamp"],
        "unread": True,
    })
    return {"id": ref.key, **stored}


def list_messages(uid: str, other_username: str) -> list:
    other_uid = accounts.lookup_uid(other_username)
    thread_id = _thread_id(uid, other_uid)
    _require_participant(thread_id, uid)
    entries = db.reference(f"dm_threads/{thread_id}/messages").get() or {}
    out = [{"id": k, **v} for k, v in entries.items()]
    out.sort(key=lambda m: m.get("timestamp") or 0)
    return out


def list_inbox(uid: str) -> list:
    """Every conversation this account has, most recently active first -
    the data behind the Messages page's conversation list."""
    threads = db.reference(f"user_threads/{uid}").get() or {}
    # A conversation with someone you have since blocked never alerts you.
    hidden = blocks.blocked_uids(uid)
    out = [{"thread_id": k, **v, "unread": bool(v.get("unread")) and v.get("other_uid") not in hidden}
           for k, v in threads.items()]
    out.sort(key=lambda t: t.get("last_timestamp") or 0, reverse=True)
    return out


def mark_read(uid: str, other_username: str) -> None:
    """The viewer has looked at this conversation - clears its unread flag.
    A no-op if the two have never messaged."""
    other_uid = accounts.lookup_uid(other_username)
    thread_id = _thread_id(uid, other_uid)
    _require_participant(thread_id, uid)
    ref = db.reference(f"user_threads/{uid}/{thread_id}")
    if ref.get() is not None:
        ref.update({"unread": False})
