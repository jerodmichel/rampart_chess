"""On-device bridge for offline vs-AI play, called from Kotlin
(ApiPlugin.kt) via Chaquopy. Mirrors the relevant subset of
server/app.py's request/response JSON shapes exactly (see that file for
the canonical version this was copied from), so the existing web/js
client code (api.js/main.js/render.js) can treat a local game exactly
like a remote one - only the transport differs. Every function here
returns a JSON string (never a raw Python object) so the Kotlin side
never has to deal with Chaquopy's PyObject conversion, just plain
strings it can hand straight to the WebView as a fetch()-shaped response.

Deliberately dropped versus app.py: accounts/auth, human-vs-human
(challenges/timers/chat) - none of that applies to a single local
anonymous vs-AI game, which is the only thing this bridge needs to
support (same shape anonymous vs-AI play already has through the real
API today).

On-device persistence (step 1 of "offline games should end up in your
Profile eventually" - syncing to the server is a later step, not done
yet): a local game is a bare in-memory GameSession with nothing else
backing it, so closing the app mid-game used to lose it outright. Every
mutating call now also writes {id, ai_color, ai_difficulty, history} as
plain JSON to a per-game file under _STORAGE_DIR, and _load_persisted_games()
(run once, at import/app-startup) rebuilds each one back into a live,
resumable GameSession by replaying its history through the same
apply_normal_move/_execute_cast_move-backed _replay_notation() the real
server already uses for its own resilience (see game_session.py's
rehydrate()/ReplayOnlyGame) - NOT that method itself, since rehydrate()
is hardcoded to ai_color=None (human-vs-human only) and this needs an AI
game; reimplemented here instead of touching that shared server code.
Only the move notation is persisted, never a snapshot of the live board -
replaying is what re-derives mate/stalemate/repetition/etc. correctly,
exactly like the server's own rehydrate() does.
"""
import json
import os

from game_session import GameSession, IllegalMoveError

_GAMES = {}

# Chaquopy docs are explicit that a bare relative filename would try to
# write to Android's (usually read-only) current directory - os.environ
# ["HOME"] is the one Chaquopy always points at this app's own writable,
# persistent-until-uninstall storage, no Java-side plumbing needed.
_STORAGE_DIR = os.path.join(os.environ.get("HOME", "."), "local_games")


def _game_path(game_id):
    return os.path.join(_STORAGE_DIR, f"{game_id}.json")


def _persist(session):
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    record = {
        "id": session.id,
        "ai_color": session.ai_color,
        "ai_difficulty": session.ai_difficulty,
        "history": session.move_log,
    }
    with open(_game_path(session.id), "w") as f:
        json.dump(record, f)


def _rehydrate_local_game(record):
    session = GameSession(ai_color=record["ai_color"], ai_difficulty=record["ai_difficulty"])
    session.id = record["id"]
    for notation in record.get("history", []):
        session._replay_notation(notation)
    return session


def _load_persisted_games():
    if not os.path.isdir(_STORAGE_DIR):
        return
    for name in os.listdir(_STORAGE_DIR):
        if not name.endswith(".json"):
            continue
        game_id = name[:-len(".json")]
        try:
            with open(os.path.join(_STORAGE_DIR, name)) as f:
                record = json.load(f)
            _GAMES[game_id] = _rehydrate_local_game(record)
        except Exception:
            # A corrupt/partial write (e.g. the app was killed mid-save)
            # shouldn't take the whole app down on next launch - losing
            # one game is fine, crashing at startup isn't.
            continue


def _serialize_cast_moves(moves_by_category):
    out = {}
    for category, moves in moves_by_category.items():
        entries = []
        for i, mv in enumerate(moves):
            entries.append({
                "index": i,
                "to": [mv.final.col, mv.final.row],
                "cards": [{"rank": c.rank, "suit": c.suit} for c in mv.cards],
            })
        out[category] = entries
    return out


def _session(game_id):
    session = _GAMES.get(game_id)
    if session is None:
        raise KeyError(f"no such local game: {game_id}")
    return session


def _ok(data):
    return json.dumps(data)


def _err(message, status):
    return json.dumps({"error": message, "status": status})


def new_game(ai_color, ai_difficulty):
    session = GameSession(ai_color=ai_color, ai_difficulty=ai_difficulty)
    _GAMES[session.id] = session
    _persist(session)
    return _ok(session.to_dict())


def get_game(game_id):
    try:
        session = _session(game_id)
    except KeyError as e:
        return _err(str(e), 404)
    return _ok(session.to_dict())


def history_at(game_id, index):
    try:
        session = _session(game_id)
        return _ok(session.state_at(index))
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)


def moves(game_id):
    try:
        session = _session(game_id)
    except KeyError as e:
        return _err(str(e), 404)
    return _ok({"moves": session.display_history()})


def legal_moves(game_id, col, row):
    try:
        session = _session(game_id)
    except KeyError as e:
        return _err(str(e), 404)
    return _ok({"destinations": session.legal_moves(col, row)})


def cast_moves(game_id):
    try:
        session = _session(game_id)
    except KeyError as e:
        return _err(str(e), 404)
    return _ok(_serialize_cast_moves(session.legal_cast_moves()))


def make_move(game_id, from_col, from_row, to_col, to_row, queen_col=None, queen_row=None):
    try:
        session = _session(game_id)
        notation = session.apply_normal_move(from_col, from_row, to_col, to_row,
                                              queen_col=queen_col, queen_row=queen_row)
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)
    _persist(session)
    state = session.to_dict()
    state["notation"] = notation
    return _ok(state)


def make_cast_move(game_id, category, index):
    try:
        session = _session(game_id)
        notation = session.apply_cast_move(category, index)
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)
    _persist(session)
    state = session.to_dict()
    state["notation"] = notation
    return _ok(state)


def cast_combo_destinations(game_id, cards_json, kind):
    try:
        session = _session(game_id)
        destinations = session.legal_cast_destinations_for_combo(json.loads(cards_json), kind)
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)
    return _ok(_serialize_cast_moves(destinations))


def cast_combo_move(game_id, cards_json, kind, to_col, to_row):
    try:
        session = _session(game_id)
        notation = session.apply_cast_combo_move(json.loads(cards_json), kind, to_col, to_row)
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)
    _persist(session)
    state = session.to_dict()
    state["notation"] = notation
    return _ok(state)


def ai_move(game_id):
    try:
        session = _session(game_id)
        notation = session.request_ai_move()
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)
    _persist(session)
    state = session.to_dict()
    state["notation"] = notation
    return _ok(state)


def resign(game_id, color):
    try:
        session = _session(game_id)
        session.resign(color)
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)
    _persist(session)
    return _ok(session.to_dict())


def abort(game_id):
    """Mirrors app.py's /abort - only valid before any move, deletes the
    session outright rather than resigning/persisting it. No uid/authorize
    check needed here (unlike app.py's), since there's only ever one local
    player and no second participant to protect this from."""
    try:
        session = _session(game_id)
    except KeyError as e:
        return _err(str(e), 404)
    if session.move_log:
        return _err("can't abort a game once a move has been made", 400)
    if session.is_game_over():
        return _err("the game is already over", 400)
    del _GAMES[game_id]
    try:
        os.remove(_game_path(game_id))
    except FileNotFoundError:
        pass
    return _ok({"status": "aborted"})


def offer_draw(game_id, color):
    try:
        session = _session(game_id)
        session.offer_draw(color)
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)
    return _ok(session.to_dict())


def respond_draw(game_id, color, accept):
    try:
        session = _session(game_id)
        session.respond_draw(color, accept)
    except KeyError as e:
        return _err(str(e), 404)
    except IllegalMoveError as e:
        return _err(str(e), 400)
    return _ok(session.to_dict())


# Runs once, when Chaquopy first imports this module (app startup) -
# repopulates _GAMES from whatever was left on disk by a previous process,
# so a game survives the app being killed/restarted.
_load_persisted_games()
