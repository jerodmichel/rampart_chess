"""Player blocking - one player hiding another from themselves.

Backed by the same Realtime Database everything else uses, written only
through this server (Admin SDK):

  blocks/{uid}/{target_uid}     -> {username, since}   # what I blocked
  blocked_by/{target_uid}/{uid} -> True                # reverse index, so
      "did they block me?" and account deletion are point reads, not scans

Blocking is deliberately quiet: the blocked player is never told. What it
does, in order of where the checks live:
  - ends any friendship between the pair (so DMs stop - DMs are friends-only)
  - stops either side sending a friend request or a challenge to the other
    (require_can_interact) - the blocked side gets a neutral message that
    doesn't reveal they were blocked
  - hides the blocked player's pending requests/challenges from the blocker
    (blocked_uids, used by friends.list_incoming / challenges.list_incoming)
  - hides the blocked player's in-game chat from the blocker (chat.list_messages)
It never removes anyone from a game already in progress - either side can
simply resign.
"""

from fastapi import HTTPException
from firebase_admin import db

import accounts


def block(uid: str, target_username: str) -> dict:
    target_uid = accounts.lookup_uid(target_username)
    if target_uid == uid:
        raise HTTPException(status_code=400, detail="you can't block yourself")
    username = db.reference(f"users/{target_uid}/username").get() or target_username
    db.reference(f"blocks/{uid}/{target_uid}").set({"username": username, "since": {".sv": "timestamp"}})
    db.reference(f"blocked_by/{target_uid}/{uid}").set(True)
    # End any friendship - both directions, same as friends.remove_friend.
    db.reference(f"friends/{uid}/{target_uid}").delete()
    db.reference(f"friends/{target_uid}/{uid}").delete()
    return {"uid": target_uid, "username": username}


def unblock(uid: str, target_username: str) -> None:
    target_uid = accounts.lookup_uid(target_username)
    db.reference(f"blocks/{uid}/{target_uid}").delete()
    db.reference(f"blocked_by/{target_uid}/{uid}").delete()


def list_blocked(uid: str) -> list:
    rows = db.reference(f"blocks/{uid}").get() or {}
    out = [{"uid": k, **v} for k, v in rows.items()]
    out.sort(key=lambda r: (r.get("username") or "").lower())
    return out


def blocked_uids(uid: str) -> set:
    """Everyone `uid` has blocked (NOT who blocked uid - that's not the
    blocker's business, and nothing needs to hide the blocker from the
    blocked player except refusing interaction, done in require_can_interact)."""
    return set((db.reference(f"blocks/{uid}").get() or {}).keys())


def require_can_interact(actor_uid: str, other_uid: str, verb: str) -> None:
    """Raises 403 if either player has blocked the other. The two cases get
    different wording on purpose: the blocker is told plainly (they need to
    know to unblock), the blocked player gets a neutral refusal that doesn't
    reveal the block. `verb` completes "You can't ___ this player."."""
    if db.reference(f"blocks/{actor_uid}/{other_uid}").get() is not None:
        raise HTTPException(status_code=403, detail="you have blocked this player - unblock them first")
    if db.reference(f"blocked_by/{actor_uid}/{other_uid}").get() is not None:
        raise HTTPException(status_code=403, detail=f"you can't {verb} this player")


def delete_for_user(uid: str) -> None:
    """Account deletion: remove every block this account made or received."""
    for target_uid in (db.reference(f"blocks/{uid}").get() or {}):
        db.reference(f"blocked_by/{target_uid}/{uid}").delete()
    db.reference(f"blocks/{uid}").delete()
    for blocker_uid in (db.reference(f"blocked_by/{uid}").get() or {}):
        db.reference(f"blocks/{blocker_uid}/{uid}").delete()
    db.reference(f"blocked_by/{uid}").delete()
