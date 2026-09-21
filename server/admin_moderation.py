#!/usr/bin/env python3
"""Owner-only moderation tool. Run from the repo root on a machine that has
server/serviceAccountKey.json (it talks to the LIVE Firebase project - the
same one local dev uses):

  python3 server/admin_moderation.py reports            # open reports, newest first
  python3 server/admin_moderation.py reports --all      # include resolved
  python3 server/admin_moderation.py resolve <report_id> ["note"]
  python3 server/admin_moderation.py suspend <username> ["reason"]
  python3 server/admin_moderation.py unsuspend <username>
  python3 server/admin_moderation.py clear-profile <username>   # blank bio + delete avatar

Suspending disables the Firebase Auth account: they cannot sign in again and
cannot refresh their session. A session that is already open keeps working
until its current ID token expires (up to ~1 hour) - that is Firebase's
normal token lifetime, and the server does not add a per-request lookup for it.
Nothing here deletes anyone's games or messages; that is intentional.
"""

import sys
import time

import firebase_auth  # noqa: F401 - initializes the Firebase Admin app on import
from firebase_admin import auth as firebase_auth_sdk
from firebase_admin import db

import account_deletion
import accounts


def _when(ms) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ms / 1000)) if ms else "?"


def cmd_reports(show_all: bool) -> None:
    rows = db.reference("reports").get() or {}
    items = [(k, v) for k, v in rows.items() if show_all or v.get("status") == "open"]
    items.sort(key=lambda kv: kv[1].get("created_at") or 0, reverse=True)
    if not items:
        print("No open reports." if not show_all else "No reports.")
        return
    for report_id, r in items:
        print(f"--- {report_id}  [{r.get('status')}]  {_when(r.get('created_at'))}")
        print(f"    {r.get('kind')} / {r.get('reason')}: {r.get('target_username')}  (reported by {r.get('reporter_username')})")
        if r.get("details"):
            print(f"    note: {r['details']}")
        if r.get("game_id"):
            print(f"    game: {r['game_id']}")
        for m in r.get("excerpt") or []:
            print(f"    msg: {m.get('text')}")
        if r.get("profile_snapshot"):
            print(f"    bio: {r['profile_snapshot'].get('bio')!r}")
        if r.get("resolution_note"):
            print(f"    resolved: {r['resolution_note']}")


def cmd_resolve(report_id: str, note: str) -> None:
    ref = db.reference(f"reports/{report_id}")
    if ref.get() is None:
        sys.exit(f"no such report: {report_id}")
    ref.update({"status": "resolved", "resolved_at": {".sv": "timestamp"}, "resolution_note": note})
    print("resolved.")


def cmd_suspend(username: str, reason: str) -> None:
    uid = accounts.lookup_uid(username)
    firebase_auth_sdk.update_user(uid, disabled=True)
    firebase_auth_sdk.revoke_refresh_tokens(uid)
    db.reference(f"suspensions/{uid}").set({"username": username, "reason": reason, "at": {".sv": "timestamp"}})
    print(f"suspended {username} ({uid}). Open sessions end within ~1 hour.")


def cmd_unsuspend(username: str) -> None:
    uid = accounts.lookup_uid(username)
    firebase_auth_sdk.update_user(uid, disabled=False)
    db.reference(f"suspensions/{uid}").delete()
    print(f"unsuspended {username}.")


def cmd_clear_profile(username: str) -> None:
    uid = accounts.lookup_uid(username)
    db.reference(f"users/{uid}").update({"bio": ""})
    account_deletion._delete_avatar(uid)
    print(f"cleared bio and avatar for {username}.")


def main(argv: list) -> None:
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    if cmd == "reports":
        cmd_reports("--all" in args)
    elif cmd == "resolve" and args:
        cmd_resolve(args[0], args[1] if len(args) > 1 else "")
    elif cmd == "suspend" and args:
        cmd_suspend(args[0], args[1] if len(args) > 1 else "")
    elif cmd == "unsuspend" and args:
        cmd_unsuspend(args[0])
    elif cmd == "clear-profile" and args:
        cmd_clear_profile(args[0])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
