"""The Players page: every registered account ranked by rating, with who's
online right now and whether the viewer may challenge them.

Presence is in-memory only (uid -> last ping, ms) - the same single-machine
assumption as app.py's GAMES dict. A signed-in page pings every minute
(web/js/header.js); anyone heard from within ONLINE_WINDOW_MS counts as
online. Nothing is written to the database for it, so it costs nothing and a
restart just means everyone shows offline until their next ping.

Two per-account privacy settings live on users/{uid} (absent = default):
  challenge_policy: "everyone" (default) | "friends"
  show_online:      true (default) | false
"""

import time

from fastapi import HTTPException
from firebase_admin import db

import ratings

ONLINE_WINDOW_MS = 150 * 1000  # a missed ping or two before dropping off
CHALLENGE_POLICIES = ("everyone", "friends")

_last_seen: dict[str, int] = {}


def _now_ms() -> int:
    return int(time.time() * 1000)


def ping(uid: str) -> None:
    _last_seen[uid] = _now_ms()


def forget(uid: str) -> None:
    _last_seen.pop(uid, None)


def is_online(uid: str, profile: dict) -> bool:
    if profile.get("show_online") is False:
        return False
    seen = _last_seen.get(uid)
    return seen is not None and _now_ms() - seen <= ONLINE_WINDOW_MS


def accepts_challenge_from(target_profile: dict, target_uid: str, from_uid: str) -> bool:
    if target_profile.get("challenge_policy", "everyone") != "friends":
        return True
    return db.reference(f"friends/{target_uid}/{from_uid}").get() is not None


def update_privacy(uid: str, challenge_policy=None, show_online=None) -> dict:
    ref = db.reference(f"users/{uid}")
    if ref.get() is None:
        raise HTTPException(status_code=404, detail="no account registered for this user")
    changes = {}
    if challenge_policy is not None:
        if challenge_policy not in CHALLENGE_POLICIES:
            raise HTTPException(status_code=400, detail='challenge_policy must be "everyone" or "friends"')
        changes["challenge_policy"] = challenge_policy
    if show_online is not None:
        changes["show_online"] = bool(show_online)
        if not show_online:
            forget(uid)
    if changes:
        ref.update(changes)
    return {"uid": uid, **ref.get()}


def list_players(viewer_uid=None, playing=None) -> list:
    """Every account: ranked players best first, then unranked new ones. Full users/ + badges/ scans - fine
    at this project's scale, same call ratings.get_rank already makes.

    Players the viewer has blocked are left out (after ranking). `can_challenge` is
    only ever true for a signed-in viewer, never for themselves, and respects
    blocks in both directions plus the target's challenge_policy. `playing`
    maps uid -> id of the live human game they're in, for a Watch link."""
    playing = playing or {}
    users = db.reference("users").get() or {}
    all_badges = db.reference("badges").get() or {}
    if viewer_uid not in users:
        viewer_uid = None  # signed in but no username claimed yet: can't challenge anyone
    viewer_friends = set()
    blocked, blocked_by = set(), set()
    if viewer_uid:
        viewer_friends = set((db.reference(f"friends/{viewer_uid}").get() or {}).keys())
        blocked = set((db.reference(f"blocks/{viewer_uid}").get() or {}).keys())
        blocked_by = set((db.reference(f"blocked_by/{viewer_uid}").get() or {}).keys())

    rows = []
    for uid, p in users.items():
        if not isinstance(p, dict) or not p.get("username"):
            continue
        is_me = uid == viewer_uid
        can_challenge = bool(
            viewer_uid and not is_me and uid not in blocked_by
            and (p.get("challenge_policy", "everyone") != "friends" or uid in viewer_friends)
        )
        rows.append({
            "uid": uid,
            "username": p["username"],
            "country": p.get("country"),
            "rating": round(p.get("rating", ratings.STARTING_RATING)),
            "peak_rating": round(p.get("peak_rating", ratings.STARTING_RATING)),
            "games_played": p.get("games_played", 0),
            "created_at": p.get("created_at"),
            "badges": all_badges.get(uid) or {},
            "online": (is_me and p.get("show_online") is not False) or is_online(uid, p),
            "playing_game_id": playing.get(uid),
            "is_me": is_me,
            "is_friend": uid in viewer_friends,
            "can_challenge": can_challenge,
            "friends_only": p.get("challenge_policy") == "friends",
        })
    # Ranked players first (rank computed before hiding blocked players, so
    # ranks agree for every viewer), then never-played accounts, unranked.
    rank_of = {uid: i + 1 for i, uid in enumerate(ratings.ranked_uids(users))}
    for r in rows:
        r["rank"] = rank_of.get(r["uid"])
    rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 0, r["username"].lower()))
    return [r for r in rows if r["uid"] not in blocked]
