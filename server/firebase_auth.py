"""Server-side Firebase wiring (Admin SDK). This is the one place server/
talks to Firebase directly - the browser client never does; it only ever
talks to this API, same as it already does for AI games. See the
project-rampart-browser-port memory note for why (server validates every
move against the real rules engine before anything reaches Firebase,
instead of trusting database security rules to catch a malicious client).

Credential path defaults to serviceAccountKey.json next to this file (local
dev); FIREBASE_CREDENTIALS_PATH overrides it for other environments (e.g. a
Cloud Run secret mounted at a different path). The key itself must never be
committed - see .gitignore.
"""

import os
from typing import Optional

import firebase_admin
from fastapi import Header, HTTPException
from firebase_admin import auth as firebase_auth_sdk
from firebase_admin import credentials

_DEFAULT_CRED_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
_CRED_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH", _DEFAULT_CRED_PATH)

# Same Realtime Database io_src_dev's pyrebase client already writes
# games/pin_mappings into - reusing it (rather than adding Firestore too)
# keeps this to one Firebase product for a solo-dev project.
_DATABASE_URL = os.environ.get(
    "FIREBASE_DATABASE_URL", "https://rampart-bea61-default-rtdb.firebaseio.com"
)

if not firebase_admin._apps:
    firebase_admin.initialize_app(
        credentials.Certificate(_CRED_PATH), {"databaseURL": _DATABASE_URL}
    )


def get_current_uid(authorization: Optional[str] = Header(None)) -> str:
    """FastAPI dependency: verifies the bearer ID token a signed-in browser
    client sends, returning the trusted Firebase uid. Raises 401 on any
    missing/malformed/invalid/expired token (uniformly - the header is
    declared optional here specifically so a missing one lands here too,
    rather than FastAPI's own validation short-circuiting it to a 422)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        # clock_skew_seconds tolerates a token being verified a moment
        # "before" its own issued-at time - a real, documented Firebase
        # edge case (not a wrong local clock - confirmed NTP-synced) when
        # a client verifies a token immediately after minting it: Google's
        # own token-issuing and token-verifying systems can disagree by a
        # sub-second amount, which a strict (default 0) check rejects.
        decoded = firebase_auth_sdk.verify_id_token(token, clock_skew_seconds=10)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid auth token: {e}")
    return decoded["uid"]


def get_optional_uid(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Like get_current_uid, but returns None instead of raising when no
    token was sent at all - for endpoints the existing anonymous
    human-vs-AI flow still needs to work without an account (see the
    _authorize_mover check in app.py). A *present but invalid* token still
    raises 401 rather than silently falling back to anonymous - that's a
    stale/bad token, not "no one signed in"."""
    if not authorization:
        return None
    return get_current_uid(authorization)
