"""Friend requests + the resulting friend graph, backed by the same
Realtime Database accounts.py/challenges.py use:

  friend_requests/{request_id} -> {
      from_uid, from_username, to_uid, to_username,
      status,       # 'pending' | 'accepted' | 'declined'
      created_at,
  }
  friends/{uid}/{friend_uid} -> {username, since}   # symmetric - written
      to BOTH uids on acceptance, so "are A and B friends" and "list A's
      friends" are both single point-reads/lists, never a query.

Mirrors challenges.py's shape deliberately (same request/accept/decline/
dismiss lifecycle) - see messages.py for the DM feature this unlocks,
gated on is_friend() below.
"""

from fastapi import HTTPException
from firebase_admin import db

import accounts


def is_friend(uid: str, other_uid: str) -> bool:
    return db.reference(f"friends/{uid}/{other_uid}").get() is not None


def _find_pending(from_uid: str, to_uid: str):
    """One indexed query (by from_uid) then an in-Python filter for to_uid
    - avoids needing a compound RTDB index for a lookup this infrequent."""
    candidates = db.reference("friend_requests").order_by_child("from_uid").equal_to(from_uid).get() or {}
    for request_id, record in candidates.items():
        if record.get("to_uid") == to_uid and record.get("status") == "pending":
            return {"request_id": request_id, **record}
    return None


def send_request(from_uid: str, from_username: str, to_username: str) -> dict:
    to_uid = accounts.lookup_uid(to_username)
    if to_uid == from_uid:
        raise HTTPException(status_code=400, detail="you can't friend yourself")
    if is_friend(from_uid, to_uid):
        raise HTTPException(status_code=409, detail="you're already friends")

    # They already asked you first - accept theirs instead of creating a
    # pointless duplicate pending request the other way.
    reverse = _find_pending(to_uid, from_uid)
    if reverse is not None:
        return accept(reverse["request_id"], from_uid)

    if _find_pending(from_uid, to_uid) is not None:
        raise HTTPException(status_code=409, detail="you already have a pending request to this player")

    record = {
        "from_uid": from_uid,
        "from_username": from_username,
        "to_uid": to_uid,
        "to_username": to_username,
        "status": "pending",
        "created_at": {".sv": "timestamp"},
    }
    ref = db.reference("friend_requests").push(record)
    return {"request_id": ref.key, **ref.get()}


def _get(request_id: str) -> dict:
    record = db.reference(f"friend_requests/{request_id}").get()
    if record is None:
        raise HTTPException(status_code=404, detail="no such friend request")
    return record


def list_incoming(uid: str) -> list:
    results = db.reference("friend_requests").order_by_child("to_uid").equal_to(uid).get() or {}
    return [{"request_id": k, **v} for k, v in results.items() if v.get("status") == "pending"]


def list_outgoing(uid: str) -> list:
    results = db.reference("friend_requests").order_by_child("from_uid").equal_to(uid).get() or {}
    return [{"request_id": k, **v} for k, v in results.items()]


def accept(request_id: str, uid: str) -> dict:
    record = _get(request_id)
    if record["to_uid"] != uid:
        raise HTTPException(status_code=403, detail="this request isn't addressed to you")
    if record["status"] != "pending":
        raise HTTPException(status_code=409, detail=f'request already {record["status"]}')

    db.reference(f"friend_requests/{request_id}").update({"status": "accepted"})
    since = {".sv": "timestamp"}
    db.reference(f"friends/{record['from_uid']}/{record['to_uid']}").set(
        {"username": record["to_username"], "since": since})
    db.reference(f"friends/{record['to_uid']}/{record['from_uid']}").set(
        {"username": record["from_username"], "since": since})
    return {"request_id": request_id, **db.reference(f"friend_requests/{request_id}").get()}


def decline(request_id: str, uid: str) -> None:
    record = _get(request_id)
    if record["to_uid"] != uid:
        raise HTTPException(status_code=403, detail="this request isn't addressed to you")
    if record["status"] != "pending":
        raise HTTPException(status_code=409, detail=f'request already {record["status"]}')
    db.reference(f"friend_requests/{request_id}").update({"status": "declined"})


def dismiss(request_id: str, uid: str) -> None:
    """Removes a request record outright, in any status - either party may
    dismiss it, same reasoning as challenges.dismiss (clearing clutter,
    not restricted to the recipient or to 'pending')."""
    record = _get(request_id)
    if uid not in (record["from_uid"], record["to_uid"]):
        raise HTTPException(status_code=403, detail="this request isn't yours to dismiss")
    db.reference(f"friend_requests/{request_id}").delete()


def list_friends(uid: str) -> list:
    results = db.reference(f"friends/{uid}").get() or {}
    return [{"uid": k, **v} for k, v in results.items()]


def remove_friend(uid: str, friend_username: str) -> None:
    friend_uid = accounts.lookup_uid(friend_username)
    if not is_friend(uid, friend_uid):
        raise HTTPException(status_code=404, detail="you're not friends with this player")
    db.reference(f"friends/{uid}/{friend_uid}").delete()
    db.reference(f"friends/{friend_uid}/{uid}").delete()
