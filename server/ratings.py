"""FIDE-style Elo ratings for human-vs-human games, per the user's spec:
standard Elo expectation, with a K-factor that's aggressive during
calibration and protective at the top:

  K = 40   first CALIBRATION_GAMES games (new players should quickly find
           their true level rather than being ground down by veterans)
  K = 20   standard, once calibrated and below MASTER_RATING
  K = 10   locked in permanently once a player's rating ever crosses
           MASTER_RATING - even if it later drops back below, a title
           this hard-won shouldn't be undone by a single blunder or a
           deliberately experimental game.

Persisted on the same users/{uid} node accounts.py already owns:
  rating          - current Elo rating (starts at STARTING_RATING)
  peak_rating     - highest rating this account has ever reached (for the
                    Stats page's "Peak Rating" headline metric)
  games_played    - count of *rated* games finished (drives the K=40
                    calibration window above)
  reached_master  - sticky bool, see K=10 above

Also appends one entry per rated game to rating_history/{uid} (a separate
top-level RTDB collection, not nested under users/{uid} - RTDB discourages
deeply nested/unbounded lists on a node that's also read whole elsewhere,
e.g. every /players/{username} call) - {rating, timestamp, game_id}, for
the Stats page's Rating Timeline chart.

Applied exactly once per finished human-vs-human game - see app.py's
_finalize_if_needed, which guards against re-applying via an in-memory
flag on the GameSession itself.
"""

from firebase_admin import db

STARTING_RATING = 1200
MASTER_RATING = 2400
CALIBRATION_GAMES = 30
K_CALIBRATION = 40
K_STANDARD = 20
K_MASTER = 10


def _k_factor(games_played: int, reached_master: bool) -> int:
    if reached_master:
        return K_MASTER
    if games_played < CALIBRATION_GAMES:
        return K_CALIBRATION
    return K_STANDARD


def _expected_score(rating: float, opponent_rating: float) -> float:
    return 1 / (1 + 10 ** ((opponent_rating - rating) / 400))


def get_rating_state(uid: str) -> dict:
    # Public - also used by badges.py to snapshot a player's rating before
    # apply_game_result below updates it (Giant Slayer/Kingslayer care
    # about the opponent's rating AT THE TIME they were beaten, not after
    # this game's own result has already moved it).
    #
    # .get(key, default) rather than requiring these fields to already
    # exist - covers any account registered before ratings existed, not
    # just ones created via accounts.register_username going forward.
    profile = db.reference(f"users/{uid}").get() or {}
    rating = profile.get("rating", STARTING_RATING)
    return {
        "rating": rating,
        "peak_rating": profile.get("peak_rating", rating),
        "games_played": profile.get("games_played", 0),
        "reached_master": profile.get("reached_master", False),
    }


def apply_game_result(session) -> None:
    """`session` must be a real two-human GameSession (both white_uid and
    black_uid set) whose result() is already non-None - enforced by the
    caller (app.py's _finalize_if_needed), not re-checked here."""
    result = session.result()
    if result["winner"] == "white":
        white_score = 1.0
    elif result["winner"] == "black":
        white_score = 0.0
    else:
        white_score = 0.5
    black_score = 1.0 - white_score

    white = get_rating_state(session.white_uid)
    black = get_rating_state(session.black_uid)

    white_expected = _expected_score(white["rating"], black["rating"])
    black_expected = 1.0 - white_expected

    white_k = _k_factor(white["games_played"], white["reached_master"])
    black_k = _k_factor(black["games_played"], black["reached_master"])

    new_white_rating = white["rating"] + white_k * (white_score - white_expected)
    new_black_rating = black["rating"] + black_k * (black_score - black_expected)

    for uid, state, new_rating in (
        (session.white_uid, white, new_white_rating),
        (session.black_uid, black, new_black_rating),
    ):
        new_rating_rounded = round(new_rating)
        db.reference(f"users/{uid}").update({
            "rating": new_rating_rounded,
            "peak_rating": max(state["peak_rating"], new_rating_rounded),
            "games_played": state["games_played"] + 1,
            "reached_master": state["reached_master"] or new_rating >= MASTER_RATING,
        })
        db.reference(f"rating_history/{uid}").push({
            "rating": new_rating_rounded,
            "timestamp": {".sv": "timestamp"},
            "game_id": session.id,
        })


def get_rating_history(uid: str) -> list:
    entries = db.reference(f"rating_history/{uid}").get() or {}
    out = [{"id": k, **v} for k, v in entries.items()]
    out.sort(key=lambda e: e.get("timestamp") or 0)
    return out


def get_rank(uid: str) -> dict:
    """Global rank + "top N%" among every registered account, by current
    rating. A full users/ scan per call - perfectly fine at this project's
    scale, not something to build a maintained sorted index for yet."""
    all_users = db.reference("users").get() or {}
    if uid not in all_users:
        return {"rank": None, "total": 0, "top_percentile": None}
    order = sorted(all_users.items(), key=lambda kv: -kv[1].get("rating", STARTING_RATING))
    total = len(order)
    rank = next(i + 1 for i, (u, _) in enumerate(order) if u == uid)
    # "Top N%" (rank 1 of 100 -> top 1%), floored at 1 so a large user base
    # never rounds a genuinely-elite rank down to "top 0%".
    top_percentile = max(1, round(100 * rank / total))
    return {"rank": rank, "total": total, "top_percentile": top_percentile}
