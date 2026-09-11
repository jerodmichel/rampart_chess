"""Username <-> uid accounts, backed by the Realtime Database.

Firebase Auth identifies people by uid (tied to an email/sign-in method),
not a name they picked - so a username is our own concept, layered on top:

  usernames/{lowercased username} -> uid   (uniqueness index)
  users/{uid}                     -> {username, created_at}

The lowercased index makes uniqueness case-insensitive ("Bob" and "bob"
can't both be claimed) while the display username keeps its original case.
"""

import re

from fastapi import HTTPException
from firebase_admin import db

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
BIO_MAX_LENGTH = 280


def _validate_username(username: str) -> str:
    # RTDB keys can't contain '.', '#', '$', '[', ']', '/' - restricting to
    # alnum/underscore sidesteps that entirely rather than trying to escape it.
    if not _USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="username must be 3-20 characters: letters, digits, underscore only",
        )
    return username


def register_username(uid: str, username: str) -> dict:
    """Claims `username` for `uid`. Raises 409 if already registered (this
    uid already has a username) or if the name is taken by someone else."""
    username = _validate_username(username)
    key = username.lower()

    existing = db.reference(f"users/{uid}").get()
    if existing is not None:
        raise HTTPException(status_code=409, detail="this account already has a username")

    def claim(current):
        if current is not None:
            raise ValueError("taken")
        return uid

    try:
        db.reference(f"usernames/{key}").transaction(claim)
    except ValueError:
        raise HTTPException(status_code=409, detail=f'username "{username}" is already taken')

    profile = {"username": username, "created_at": {".sv": "timestamp"}}
    db.reference(f"users/{uid}").set(profile)
    return {"uid": uid, "username": username}


def get_profile(uid: str) -> dict:
    profile = db.reference(f"users/{uid}").get()
    if profile is None:
        raise HTTPException(status_code=404, detail="no account registered for this user")
    return {"uid": uid, **profile}


def update_bio(uid: str, bio: str) -> dict:
    """`bio` may be an empty string (clearing it) - only length is
    validated. Requires an existing account (a username already claimed),
    same as any other profile field."""
    if len(bio) > BIO_MAX_LENGTH:
        raise HTTPException(status_code=400, detail=f"bio must be {BIO_MAX_LENGTH} characters or fewer")
    ref = db.reference(f"users/{uid}")
    if ref.get() is None:
        raise HTTPException(status_code=404, detail="no account registered for this user")
    ref.update({"bio": bio})
    return get_profile(uid)


def lookup_uid(username: str) -> str:
    """Resolves a username to its uid, for challenging/matching a player by
    name instead of sharing an id (404 if no such username)."""
    uid = db.reference(f"usernames/{username.lower()}").get()
    if uid is None:
        raise HTTPException(status_code=404, detail=f'no user named "{username}"')
    return uid
