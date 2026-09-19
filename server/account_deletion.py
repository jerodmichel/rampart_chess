"""Self-service account deletion (required by Google Play for any app that
lets people create accounts).

Policy, matching web/legal.html and web/delete-account.html:
  - Deleted outright: profile, username (freed for reuse), avatar, badges,
    rating history, friends (both directions), friend requests, challenges,
    DM threads (both sides), and the user's game index.
  - Anonymized, NOT deleted: finished human-vs-human game records and their
    in-game chat - the opponent's own history depends on them. The user's
    uid becomes a random "deleted_xxxxxxxx" placeholder (not None: badges.py
    and app.py treat "both uids set" as "a real human-vs-human game") and
    their username becomes "Deleted user".
  - Finished/abandoned vs-AI games have no other human involved, so those
    records are deleted outright.

Every step is safe to re-run, and the Firebase Auth user goes last, so a
failure partway through can just be retried by the user.
"""

import logging
import secrets

from fastapi import HTTPException
from firebase_admin import auth as firebase_auth_sdk
from firebase_admin import db, storage

logger = logging.getLogger(__name__)

_AVATAR_BUCKET = "rampart-bea61.firebasestorage.app"
DELETED_USERNAME = "Deleted user"


def _side_of(record: dict, uid: str):
    """'white'/'black' for the side `uid` played in this record, else None."""
    if record.get("white_uid") == uid:
        return "white"
    if record.get("black_uid") == uid:
        return "black"
    return None


def _plan_games(uid: str):
    """Returns (records_by_id, blocking_game_ids). Raises nothing itself so
    the caller can refuse before any deletion has happened."""
    game_ids = db.reference(f"user_games/{uid}").get() or {}
    records = {}
    blocking = []
    for game_id in game_ids:
        record = db.reference(f"game_records/{game_id}").get()
        if record is None:
            continue
        records[game_id] = record
        side = _side_of(record, uid)
        other_uid = record.get("black_uid" if side == "white" else "white_uid")
        # No "result" key at all means still in progress (see game_records.py).
        if record.get("result") is None and other_uid is not None:
            blocking.append(game_id)
    return records, blocking


def _anonymize_games(uid: str, records: dict, tombstone: str) -> None:
    for game_id, record in records.items():
        side = _side_of(record, uid)
        if side is None:
            continue
        other_uid = record.get("black_uid" if side == "white" else "white_uid")
        if other_uid is None:
            # vs-AI: nobody else's history depends on this record.
            db.reference(f"game_records/{game_id}").delete()
            db.reference(f"game_chat/{game_id}").delete()
            continue
        db.reference(f"game_records/{game_id}").update({
            f"{side}_uid": tombstone,
            f"{side}_username": DELETED_USERNAME,
        })
        messages = db.reference(f"game_chat/{game_id}").get() or {}
        for message_id, message in messages.items():
            if message.get("uid") == uid:
                db.reference(f"game_chat/{game_id}/{message_id}").update({
                    "uid": tombstone,
                    "username": DELETED_USERNAME,
                })


def _delete_friends(uid: str) -> None:
    for friend_uid in (db.reference(f"friends/{uid}").get() or {}):
        db.reference(f"friends/{friend_uid}/{uid}").delete()
    db.reference(f"friends/{uid}").delete()
    for field in ("from_uid", "to_uid"):
        rows = db.reference("friend_requests").order_by_child(field).equal_to(uid).get() or {}
        for request_id in rows:
            db.reference(f"friend_requests/{request_id}").delete()


def _delete_challenges(uid: str) -> None:
    for field in ("from_uid", "to_uid"):
        rows = db.reference("challenges").order_by_child(field).equal_to(uid).get() or {}
        for challenge_id in rows:
            db.reference(f"challenges/{challenge_id}").delete()


def _delete_dms(uid: str) -> None:
    threads = db.reference(f"user_threads/{uid}").get() or {}
    for thread_id, meta in threads.items():
        db.reference(f"dm_threads/{thread_id}").delete()
        other_uid = (meta or {}).get("other_uid")
        if other_uid:
            db.reference(f"user_threads/{other_uid}/{thread_id}").delete()
    db.reference(f"user_threads/{uid}").delete()


def _delete_avatar(uid: str) -> None:
    try:
        storage.bucket(_AVATAR_BUCKET).blob(f"avatars/{uid}").delete()
    except Exception:
        # No avatar uploaded (404) is the common case; anything else must
        # not block the rest of the deletion.
        logger.info("no avatar deleted for %s", uid, exc_info=True)


def delete_account(uid: str, confirm_username: str) -> dict:
    profile = db.reference(f"users/{uid}").get()
    username = (profile or {}).get("username")

    # On a retry after a partial failure the profile may already be gone;
    # the recent-login requirement still protects that case.
    if username is not None and confirm_username.strip().lower() != username.lower():
        raise HTTPException(status_code=400, detail="typed username does not match")

    records, blocking = _plan_games(uid)
    if blocking:
        raise HTTPException(
            status_code=409,
            detail="you have a game in progress - finish or resign it before deleting your account",
        )

    tombstone = f"deleted_{secrets.token_hex(4)}"
    _anonymize_games(uid, records, tombstone)
    db.reference(f"user_games/{uid}").delete()
    _delete_friends(uid)
    _delete_challenges(uid)
    _delete_dms(uid)
    db.reference(f"badges/{uid}").delete()
    db.reference(f"rating_history/{uid}").delete()
    _delete_avatar(uid)

    # Profile + username index last: they're what the confirmation check
    # above reads, and what keeps a half-deleted account still "findable".
    if username is not None:
        index = db.reference(f"usernames/{username.lower()}")
        if index.get() == uid:
            index.delete()
    db.reference(f"users/{uid}").delete()

    try:
        firebase_auth_sdk.delete_user(uid)
    except firebase_auth_sdk.UserNotFoundError:
        pass
    logger.info("deleted account %s (%d game records touched)", uid, len(records))
    return {"deleted": True}
