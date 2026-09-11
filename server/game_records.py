"""Durable records of games played by a signed-in account, backed by the
same Realtime Database accounts.py/challenges.py use:

  game_records/{game_id} -> {
      id, white_uid, black_uid, white_username, black_username,
      ai_difficulty,   # only present for a vs-AI game - see below
      time_control,
      history,   # the move log - everything needed to replay the game
      result,    # {winner, reason} | None while still in progress
      created_at, updated_at,
  }
  user_games/{uid}/{game_id} -> True   # fan-out index for "my games"

A game is persisted whenever AT LEAST ONE side has a real uid attached -
always true for human-vs-human (both do), and true for a vs-AI game only
if the human was signed in when they started it (app.py's new_game tags
their own color with their uid then, leaving the AI's "color" uid-less -
there's no account on that side to attach anything to). Anonymous vs-AI
play (still fully supported, no account required) has neither uid set and
is never persisted, since there'd be nothing to list it under.

This is also what lets a game survive server/'s otherwise in-memory-only
GAMES dict across a restart - see GameSession.ReplayOnlyGame for the
read-only reconstruction that uses it, and app.py's get_view for where
that fallback kicks in.

Written after every mutating action (not just at the end) - so an
interrupted game is still visible up to whatever point it reached, not
silently lost.
"""

from firebase_admin import db


def save_game_record(session, white_username: str = None, black_username: str = None,
                      ai_difficulty: str = None) -> None:
    """white_username/black_username/ai_difficulty are only ever passed at
    creation (app.py's accept_challenge/new_game already have them) and,
    like created_at, never overwritten on later calls - a profile's game
    ledger shows the name/difficulty from when the game was played, not a
    live-updated one, matching how lichess/chess.com history works."""
    if session.white_uid is None and session.black_uid is None:
        return  # fully anonymous - no account on either side to attach to

    ref = db.reference(f"game_records/{session.id}")
    record = {
        "id": session.id,
        "white_uid": session.white_uid,
        "black_uid": session.black_uid,
        "time_control": session.time_control,
        "history": session.move_log,
        # NB: RTDB's update() treats a None value as "delete this key", not
        # "store a null" - so while a game is ongoing, the stored record
        # has NO "result" key at all rather than "result": null. Always
        # read it with .get("result") (as ReplayOnlyGame does), never
        # ["result"], or an in-progress game raises KeyError.
        "result": session.result(),
        "updated_at": {".sv": "timestamp"},
    }
    if ref.get() is None:
        record["created_at"] = {".sv": "timestamp"}
        if white_username is not None:
            record["white_username"] = white_username
        if black_username is not None:
            record["black_username"] = black_username
        if ai_difficulty is not None:
            record["ai_difficulty"] = ai_difficulty
    # update() merges rather than replaces the node, so created_at/the
    # usernames/difficulty (only ever included on the first save) are left
    # untouched on later ones.
    ref.update(record)

    # Only fan out for a side that actually has an account - the AI's
    # "color" in a vs-AI game has none, and there's no uid-less user_games
    # bucket to write to.
    if session.white_uid:
        db.reference(f"user_games/{session.white_uid}/{session.id}").set(True)
    if session.black_uid:
        db.reference(f"user_games/{session.black_uid}/{session.id}").set(True)


def get_game_record(game_id: str):
    return db.reference(f"game_records/{game_id}").get()


def list_games_for_uid(uid: str) -> list:
    game_ids = db.reference(f"user_games/{uid}").get() or {}
    records = []
    for game_id in game_ids:
        record = get_game_record(game_id)
        if record is not None:
            records.append(record)
    records.sort(key=lambda r: r.get("updated_at") or 0, reverse=True)
    return records
