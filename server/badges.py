"""Phase 1 achievement badges - the ones backed entirely by data
ratings.py/game_records.py already track (rating, peak_rating,
games_played, move count), no new in-game tracking required. See
web/js/badges.js for the matching display metadata (name/description/
placeholder icon per id) - this file only owns which ids exist and when
they're earned.

Nemesis/Unbreakable/The Grind (added later) are derived from persisted
game_records/user_games history - see _decisive_history_vs/_check_grind
below. The Trap is now "Mate by Capture" - Rampart's own win condition
(landing on the enemy king house while their king sits off a card square,
distinct from an ordinary no-legal-moves checkmate) rather than the
originally-proposed "opponent still has a majority of pieces" version,
which would have needed live piece-capture tracking. Still deferred:
Flawless Victory, From the Brink - these still need that tracking
(board.py's `_raise_raider`/`_raise_queen` can pull a piece back OUT of a
player's own grave mid-game, so "pieces remaining on the board" is not
monotonic and a full-game replay would be needed to know whether a piece
was ever lost, or how low a player's board count ever dropped - not just
the final position).

Storage: badges/{uid}/{badge_id} -> {unlocked_at: server timestamp}.
Permanent once written - never re-evaluated or removed, matching "unlocks
the medal forever, even if their rating later drops" for the Ladder
trophies, and simply not applicable to the others (a win/games-played
count never un-happens).

First Blood is winner-only, gated on result()["reason"] == "checkmate" -
deliberately NOT awarded for a win by resignation/timeout, and not for
just completing a match (that was the badge's original, easier-to-earn
shape; the user wanted it to actually mean "your first kill" in a
perfect-information game, so it now lives alongside Giant Slayer/
Kingslayer/Blitzkrieg as a winner-only condition check rather than in
TENURE).

Only ever checked for a rated (human-vs-human) game, right after
ratings.apply_game_result - called from app.py's _finalize_if_needed,
which already gates on session.white_uid and session.black_uid both being
set. An AI game never reaches this (see the user's explicit call: Tenure/
Ladder badges track rated games only, matching how games_played/rating
already work)."""

from firebase_admin import db

import game_records

# (badge_id, threshold) - peak_rating >= threshold unlocks it permanently.
LADDER = [
    ("adept", 1500),
    ("tactician", 1800),
    ("vanguard", 2000),
    ("apex", 2200),
]

# (badge_id, threshold) - games_played >= threshold.
TENURE = [
    ("centurion", 100),
    ("veteran", 1000),
]

# Placeholder thresholds - easy to retune once real play data shows what
# "an upset" or "a fast win" actually looks like at this game's pace.
GIANT_SLAYER_MARGIN = 150
KINGSLAYER_MIN_RATING = 2000  # "holds the Vanguard or Apex rank"
BLITZKRIEG_MAX_PLIES = 20  # len(move_log) is in plies (half-moves), not full moves
NEMESIS_STREAK = 3  # beat the exact same opponent this many times in a row
UNBREAKABLE_LOOKBACK = 3  # opponent's last-N encounters must all be losses for you
GRIND_COUNT = 5
GRIND_WINDOW_HOURS = 24


def _decisive_history_vs(uid: str, opponent_uid: str) -> list:
    """['win'|'loss', ...] in chronological order, from uid's perspective,
    for finished DECISIVE (checkmate/resignation/timeout - never a draw or
    a still-in-progress game) rated games between uid and opponent_uid.
    Includes the just-finished game itself: save_game_record already ran
    before check_and_award (see app.py's _finalize_if_needed), so this
    game's own record is already in game_records/user_games by the time
    Nemesis/Unbreakable are checked below."""
    dated = []
    for record in game_records.list_games_for_uid(uid):
        if record.get("white_uid") == uid and record.get("black_uid") == opponent_uid:
            my_color = "white"
        elif record.get("black_uid") == uid and record.get("white_uid") == opponent_uid:
            my_color = "black"
        else:
            continue  # a game against a different opponent
        result = record.get("result")
        if not result or result.get("winner") not in ("white", "black"):
            continue  # still in progress, or a draw
        timestamp = record.get("created_at") or record.get("updated_at") or 0
        dated.append((timestamp, "win" if result["winner"] == my_color else "loss"))
    dated.sort(key=lambda pair: pair[0])
    return [outcome for _, outcome in dated]


def _check_nemesis(winner_uid: str, loser_uid: str) -> bool:
    history = _decisive_history_vs(winner_uid, loser_uid)
    return len(history) >= NEMESIS_STREAK and all(o == "win" for o in history[-NEMESIS_STREAK:])


def _check_unbreakable(winner_uid: str, loser_uid: str) -> bool:
    history = _decisive_history_vs(winner_uid, loser_uid)
    if len(history) < UNBREAKABLE_LOOKBACK + 1 or history[-1] != "win":
        return False
    prior_encounters = history[-(UNBREAKABLE_LOOKBACK + 1):-1]
    return all(o == "loss" for o in prior_encounters)


def _check_grind(uid: str) -> bool:
    """5 rated matches completed inside any rolling 24-hour window."""
    timestamps = sorted(
        record["updated_at"] for record in game_records.list_games_for_uid(uid)
        if record.get("result") and record.get("updated_at")
    )
    window_ms = GRIND_WINDOW_HOURS * 3600 * 1000
    for i in range(len(timestamps) - GRIND_COUNT + 1):
        if timestamps[i + GRIND_COUNT - 1] - timestamps[i] <= window_ms:
            return True
    return False


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
        if _check_grind(uid) and _award(uid, "the_grind"):
            newly_unlocked[uid].append("the_grind")

    if loser_pre_rating - winner_pre_rating >= GIANT_SLAYER_MARGIN and _award(winner_uid, "giant_slayer"):
        newly_unlocked[winner_uid].append("giant_slayer")
    if loser_pre_rating >= KINGSLAYER_MIN_RATING and _award(winner_uid, "kingslayer"):
        newly_unlocked[winner_uid].append("kingslayer")
    if len(session.move_log) <= BLITZKRIEG_MAX_PLIES and _award(winner_uid, "blitzkrieg"):
        newly_unlocked[winner_uid].append("blitzkrieg")
    if result["reason"] == "checkmate" and _award(winner_uid, "first_blood"):
        newly_unlocked[winner_uid].append("first_blood")
    if _check_nemesis(winner_uid, loser_uid) and _award(winner_uid, "nemesis"):
        newly_unlocked[winner_uid].append("nemesis")
    if _check_unbreakable(winner_uid, loser_uid) and _award(winner_uid, "unbreakable"):
        newly_unlocked[winner_uid].append("unbreakable")
    if result["reason"] == "mate_by_capture" and _award(winner_uid, "mate_by_capture"):
        newly_unlocked[winner_uid].append("mate_by_capture")

    return {uid: earned for uid, earned in newly_unlocked.items() if earned}
