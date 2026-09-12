"""Phase 1 achievement badges - the ones backed entirely by data
ratings.py/game_records.py already track (rating, peak_rating,
games_played, move count), no new in-game tracking required. See
web/js/badges.js for the matching display metadata (name/description/
placeholder icon per id) - this file only owns which ids exist and when
they're earned.

Deferred to a later phase (need head-to-head game history or live
piece-capture tracking, neither of which exists yet): Nemesis, Unbreakable,
The Grind, Flawless Victory, From the Brink, Checkmate/The Trap.

Storage: badges/{uid}/{badge_id} -> {unlocked_at: server timestamp}.
Permanent once written - never re-evaluated or removed, matching "unlocks
the medal forever, even if their rating later drops" for the Ladder
trophies, and simply not applicable to the others (a win/games-played
count never un-happens).

Only ever checked for a rated (human-vs-human) game, right after
ratings.apply_game_result - called from app.py's _finalize_if_needed,
which already gates on session.white_uid and session.black_uid both being
set. An AI game never reaches this (see the user's explicit call: Tenure/
Ladder badges track rated games only, matching how games_played/rating
already work)."""

from firebase_admin import db

# (badge_id, threshold) - peak_rating >= threshold unlocks it permanently.
LADDER = [
    ("adept", 1500),
    ("tactician", 1800),
    ("vanguard", 2000),
    ("apex", 2200),
]

# (badge_id, threshold) - games_played >= threshold.
TENURE = [
    ("first_blood", 1),
    ("centurion", 100),
    ("veteran", 1000),
]

# Placeholder thresholds - easy to retune once real play data shows what
# "an upset" or "a fast win" actually looks like at this game's pace.
GIANT_SLAYER_MARGIN = 150
KINGSLAYER_MIN_RATING = 2000  # "holds the Vanguard or Apex rank"
BLITZKRIEG_MAX_PLIES = 20  # len(move_log) is in plies (half-moves), not full moves


def _award(uid: str, badge_id: str) -> bool:
    """True if this call newly unlocked the badge, False if the player
    already had it (never re-written - unlocked_at should stay the first
    time it was earned)."""
    ref = db.reference(f"badges/{uid}/{badge_id}")
    if ref.get() is not None:
        return False
    ref.set({"unlocked_at": {".sv": "timestamp"}})
    return True


def get_badges(uid: str) -> dict:
    return db.reference(f"badges/{uid}").get() or {}


def check_and_award(session, pre_game_white_rating: float, pre_game_black_rating: float) -> dict:
    """Evaluates every phase-1 badge for both players of a just-finished
    rated game and returns {uid: [newly unlocked badge ids]} (only for
    players who earned something new). Must be called AFTER
    ratings.apply_game_result, so peak_rating/games_played are already the
    post-game values - but pre_game_*_rating is passed in separately since
    Giant Slayer/Kingslayer are about the opponent's rating at the moment
    you beat them, before this game's own result could move it."""
    result = session.result()
    if result is None or result.get("winner") is None:
        return {}
    winner_color = result["winner"]
    winner_uid = session.white_uid if winner_color == "white" else session.black_uid
    loser_uid = session.black_uid if winner_color == "white" else session.white_uid
    winner_pre_rating = pre_game_white_rating if winner_color == "white" else pre_game_black_rating
    loser_pre_rating = pre_game_black_rating if winner_color == "white" else pre_game_white_rating

    newly_unlocked = {winner_uid: [], loser_uid: []}

    for uid in (winner_uid, loser_uid):
        profile = db.reference(f"users/{uid}").get() or {}
        peak = profile.get("peak_rating", profile.get("rating", 0))
        games_played = profile.get("games_played", 0)
        for badge_id, threshold in LADDER:
            if peak >= threshold and _award(uid, badge_id):
                newly_unlocked[uid].append(badge_id)
        for badge_id, threshold in TENURE:
            if games_played >= threshold and _award(uid, badge_id):
                newly_unlocked[uid].append(badge_id)

    if loser_pre_rating - winner_pre_rating >= GIANT_SLAYER_MARGIN and _award(winner_uid, "giant_slayer"):
        newly_unlocked[winner_uid].append("giant_slayer")
    if loser_pre_rating >= KINGSLAYER_MIN_RATING and _award(winner_uid, "kingslayer"):
        newly_unlocked[winner_uid].append("kingslayer")
    if len(session.move_log) <= BLITZKRIEG_MAX_PLIES and _award(winner_uid, "blitzkrieg"):
        newly_unlocked[winner_uid].append("blitzkrieg")

    return {uid: earned for uid, earned in newly_unlocked.items() if earned}
