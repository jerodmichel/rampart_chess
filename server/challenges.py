"""Match invites ("challenges"), backed by the same Realtime Database
accounts.py uses:

  challenges/{challenge_id} -> {
      from_uid, from_username, to_uid, to_username,
      challenger_color,   # 'white' | 'black' - resolved at creation time
      time_control,       # one of TIME_CONTROLS, chosen by the challenger
      status,             # 'pending' | 'accepted' | 'declined'
      created_at, game_id (present once accepted),
  }

Always keyed/checked by uid, never trusted from a client-supplied username
directly - accounts.lookup_uid() is the only thing allowed to turn a
username into a uid. This module only manages the challenge record itself;
creating the actual GameSession on acceptance is app.py's job (keeps this
module from needing to know about GameSession/GAMES at all).
"""

import random

from fastapi import HTTPException
from firebase_admin import db

import accounts

# Kept as a plain local constant (rather than importing GameSession.
# TIME_CONTROLS) so this module still doesn't need to know GameSession
# exists at all - it just validates and stores a string.
TIME_CONTROLS = ("30min", "1hour", "1day_per_move")


def create_challenge(from_uid: str, from_username: str, to_username: str, color: str = "random",
                      time_control: str = "30min") -> dict:
    to_uid = accounts.lookup_uid(to_username)
    if to_uid == from_uid:
        raise HTTPException(status_code=400, detail="you can't challenge yourself")

    if color == "random":
        challenger_color = random.choice(["white", "black"])
    elif color in ("white", "black"):
        challenger_color = color
    else:
        raise HTTPException(status_code=400, detail='color must be "white", "black", or "random"')

    if time_control not in TIME_CONTROLS:
        raise HTTPException(status_code=400, detail=f"time_control must be one of {TIME_CONTROLS}")

    record = {
        "from_uid": from_uid,
        "from_username": from_username,
        "to_uid": to_uid,
        "to_username": to_username,
        "challenger_color": challenger_color,
        "time_control": time_control,
        "status": "pending",
        "created_at": {".sv": "timestamp"},
    }
    ref = db.reference("challenges").push(record)
    # re-fetch rather than echoing `record` back: created_at was a
    # {'.sv': 'timestamp'} sentinel locally, and only the stored copy has
    # the real server-resolved value.
    return {"challenge_id": ref.key, **ref.get()}


def _get(challenge_id: str) -> dict:
    record = db.reference(f"challenges/{challenge_id}").get()
    if record is None:
        raise HTTPException(status_code=404, detail="no such challenge")
    return record


def list_incoming(uid: str) -> list:
    results = db.reference("challenges").order_by_child("to_uid").equal_to(uid).get() or {}
    return [{"challenge_id": k, **v} for k, v in results.items() if v.get("status") == "pending"]


def list_outgoing(uid: str) -> list:
    results = db.reference("challenges").order_by_child("from_uid").equal_to(uid).get() or {}
    return [{"challenge_id": k, **v} for k, v in results.items()]


def accept(challenge_id: str, uid: str) -> dict:
    """Validates that `uid` may accept this challenge and returns the
    record; does not itself create a game or mark it accepted - see
    mark_accepted, called by app.py once the GameSession actually exists."""
    record = _get(challenge_id)
    if record["to_uid"] != uid:
        raise HTTPException(status_code=403, detail="this challenge isn't addressed to you")
    if record["status"] != "pending":
        raise HTTPException(status_code=409, detail=f'challenge already {record["status"]}')
    return record


def decline(challenge_id: str, uid: str) -> None:
    record = _get(challenge_id)
    if record["to_uid"] != uid:
        raise HTTPException(status_code=403, detail="this challenge isn't addressed to you")
    if record["status"] != "pending":
        raise HTTPException(status_code=409, detail=f'challenge already {record["status"]}')
    db.reference(f"challenges/{challenge_id}").update({"status": "declined"})


def mark_accepted(challenge_id: str, game_id: str) -> None:
    db.reference(f"challenges/{challenge_id}").update({"status": "accepted", "game_id": game_id})


def dismiss(challenge_id: str, uid: str) -> None:
    """Removes a challenge record outright - for clearing clutter (a
    pending invite you're no longer interested in, or an accepted one whose
    game is gone because /games is in-memory-only and doesn't survive a
    server restart). Either side of the challenge may dismiss it, in any
    status - unlike accept/decline this isn't restricted to the recipient
    or to 'pending', since the whole point is cleaning up regardless of
    state."""
    record = _get(challenge_id)
    if uid not in (record["from_uid"], record["to_uid"]):
        raise HTTPException(status_code=403, detail="this challenge isn't yours to dismiss")
    db.reference(f"challenges/{challenge_id}").delete()
