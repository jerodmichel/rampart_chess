"""Per-game chat, backed by the same Realtime Database accounts.py/
game_records.py/challenges.py use:

  game_chat/{game_id}/{message_id} -> {
      uid, username, text, timestamp,
  }

Participant-only, both to send and to read - chat only exists for a real
two-human game (app.py gates both endpoints the same way offer_draw is
gated, via _participant_color), so there's no anonymous/spectator/AI-side
chat to support here.
"""

from firebase_admin import db
from fastapi import HTTPException

MAX_MESSAGE_LENGTH = 500


def send_message(game_id: str, uid: str, username: str, text: str) -> dict:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="message can't be empty")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"message can't exceed {MAX_MESSAGE_LENGTH} characters")
    record = {
        "uid": uid,
        "username": username,
        "text": text,
        "timestamp": {".sv": "timestamp"},
    }
    ref = db.reference(f"game_chat/{game_id}").push(record)
    # re-fetch rather than echoing `record` back - timestamp was a
    # {'.sv': 'timestamp'} sentinel locally, only the stored copy has the
    # real server-resolved value (same reason challenges.create_challenge does this).
    return {"id": ref.key, **ref.get()}


def list_messages(game_id: str) -> list:
    results = db.reference(f"game_chat/{game_id}").get() or {}
    messages = [{"id": k, **v} for k, v in results.items()]
    messages.sort(key=lambda m: m.get("timestamp") or 0)
    return messages
