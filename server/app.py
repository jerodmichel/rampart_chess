"""Minimal HTTP API wrapping the Rampart game/AI logic in io_src_dev_ai, for
a future browser client. This is step 1 of the browser port: prove the
existing Python rules engine + AI can run headless behind an API, before any
JS/rendering work happens. In-memory game storage only for now (fine for
local testing; a real deployment would move this to Firestore so state
survives across Cloud Run instances/restarts)."""

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import accounts
import challenges
import game_records
from firebase_auth import get_current_uid, get_optional_uid
from game_session import GameSession, IllegalMoveError, ReplayOnlyGame

app = FastAPI(title="Rampart API")

# wide-open for local dev; tighten to the real client origin before deploying
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GAMES: dict[str, GameSession] = {}


def get_session(game_id: str) -> GameSession:
    """For endpoints that MUTATE a game - only ever a live, in-memory
    GameSession, never the read-only ReplayOnlyGame get_view can return.
    A game whose id is only in the persisted record (its live GameSession
    was lost to a server restart) gets a clearer error than a bare 404,
    since that's a meaningfully different situation from an id that never
    existed at all."""
    session = GAMES.get(game_id)
    if session is not None:
        return session
    if game_records.get_game_record(game_id) is not None:
        raise HTTPException(
            status_code=409,
            detail="this game was interrupted by a server restart and can no longer be continued "
                   "(it's still viewable, just not playable)",
        )
    raise HTTPException(status_code=404, detail=f"no game with id {game_id}")


def get_view(game_id: str):
    """For read-only endpoints - a live GameSession if one exists, else a
    ReplayOnlyGame reconstructed from its persisted record if it has one.
    Both support to_dict()/state_at(), which is all these endpoints need."""
    session = GAMES.get(game_id)
    if session is not None:
        return session
    record = game_records.get_game_record(game_id)
    if record is not None:
        return ReplayOnlyGame(record)
    raise HTTPException(status_code=404, detail=f"no game with id {game_id}")


def _authorize_mover(session: GameSession, uid: Optional[str]) -> None:
    """A game created via /challenges has a real uid on file for each
    color; a game created via /games (human-vs-AI) has both left None and
    is unrestricted, exactly as it's always worked - no account required to
    play the AI. Only enforced here, at the point a move actually mutates
    the game; read-only endpoints (legal_moves, cast_combo_destinations,
    GET /games/{id}) stay open to either side."""
    expected = session.white_uid if session.next_player == "white" else session.black_uid
    if expected is None:
        return
    if uid != expected:
        raise HTTPException(status_code=403, detail="it isn't your turn in this game")


def _resigning_color(session: GameSession, uid: Optional[str]) -> str:
    """Unlike a move, resigning isn't gated by whose turn it is - either
    participant can resign at any time. An AI game has exactly one human
    (whichever color isn't the AI's), so no account is needed to identify
    who's resigning there, same as the rest of that mode."""
    if session.ai_color is not None:
        return "black" if session.ai_color == "white" else "white"
    if uid == session.white_uid:
        return "white"
    if uid == session.black_uid:
        return "black"
    raise HTTPException(status_code=403, detail="you are not a participant in this game")


def _participant_color(session: GameSession, uid: Optional[str]) -> str:
    """Draw offers only make sense between two real opponents - there's no
    one for an AI to negotiate with."""
    if session.white_uid is None and session.black_uid is None:
        raise HTTPException(status_code=400, detail="this game has no opponent to offer a draw to")
    if uid == session.white_uid:
        return "white"
    if uid == session.black_uid:
        return "black"
    raise HTTPException(status_code=403, detail="you are not a participant in this game")


class NewGameRequest(BaseModel):
    ai_color: str = "black"
    ai_difficulty: str = "Medium"


# -- accounts -----------------------------------------------------------
#
# The browser signs in directly with Firebase Auth's own client SDK and
# sends the resulting ID token here as a bearer token; get_current_uid
# verifies it server-side (Admin SDK) rather than trusting a client-supplied
# uid. Firebase Auth has no concept of a chosen username, so that's tracked
# in accounts.py's own username<->uid mapping on top of it.

class RegisterRequest(BaseModel):
    username: str


@app.post("/auth/register")
def register(req: RegisterRequest, uid: str = Depends(get_current_uid)):
    return accounts.register_username(uid, req.username)


@app.get("/auth/me")
def get_me(uid: str = Depends(get_current_uid)):
    return accounts.get_profile(uid)


@app.get("/auth/users/{username}")
def find_user(username: str, uid: str = Depends(get_current_uid)):
    """Resolves a username to a uid, for challenging/matching a player by
    name instead of sharing a game id."""
    return {"username": username, "uid": accounts.lookup_uid(username)}


# -- challenges (match invites) ------------------------------------------
#
# The actual human-vs-human GameSession is only ever created here, on
# acceptance - challenges.py itself only manages the invite record, so it
# has no reason to import GameSession/GAMES.

class ChallengeRequest(BaseModel):
    to_username: str
    color: str = "random"  # 'white' | 'black' | 'random' - the CHALLENGER's color
    time_control: str = "30min"  # one of challenges.TIME_CONTROLS


@app.post("/challenges")
def create_challenge(req: ChallengeRequest, uid: str = Depends(get_current_uid)):
    profile = accounts.get_profile(uid)
    return challenges.create_challenge(
        uid, profile["username"], req.to_username, req.color, req.time_control)


@app.get("/challenges/incoming")
def list_incoming_challenges(uid: str = Depends(get_current_uid)):
    return challenges.list_incoming(uid)


@app.get("/challenges/outgoing")
def list_outgoing_challenges(uid: str = Depends(get_current_uid)):
    return challenges.list_outgoing(uid)


@app.post("/challenges/{challenge_id}/accept")
def accept_challenge(challenge_id: str, uid: str = Depends(get_current_uid)):
    record = challenges.accept(challenge_id, uid)
    challenger_is_white = record["challenger_color"] == "white"
    white_uid = record["from_uid"] if challenger_is_white else record["to_uid"]
    black_uid = record["to_uid"] if challenger_is_white else record["from_uid"]
    white_username = record["from_username"] if challenger_is_white else record["to_username"]
    black_username = record["to_username"] if challenger_is_white else record["from_username"]

    session = GameSession(ai_color=None, white_uid=white_uid, black_uid=black_uid,
                           time_control=record.get("time_control"))
    GAMES[session.id] = session
    challenges.mark_accepted(challenge_id, session.id)
    game_records.save_game_record(session, white_username, black_username)
    return session.to_dict()


@app.post("/challenges/{challenge_id}/decline")
def decline_challenge(challenge_id: str, uid: str = Depends(get_current_uid)):
    challenges.decline(challenge_id, uid)
    return {"status": "declined"}


@app.post("/challenges/{challenge_id}/dismiss")
def dismiss_challenge(challenge_id: str, uid: str = Depends(get_current_uid)):
    """Removes a challenge record outright, in any status - for clearing
    clutter (an old accepted challenge whose in-memory game is gone after a
    server restart, or a pending one you're no longer interested in)."""
    challenges.dismiss(challenge_id, uid)
    return {"status": "dismissed"}


class NormalMoveRequest(BaseModel):
    from_col: int
    from_row: int
    to_col: int
    to_row: int


class CastMoveRequest(BaseModel):
    category: str  # 'strike' | 'raise_raider' | 'raise_queen'
    index: int


class CardSpec(BaseModel):
    rank: int
    suit: int


class CastComboDestinationsRequest(BaseModel):
    cards: list[CardSpec]
    kind: str  # 'strike' | 'raise'


class CastComboMoveRequest(BaseModel):
    cards: list[CardSpec]
    kind: str  # 'strike' | 'raise'
    to_col: int
    to_row: int


def _serialize_cast_moves(moves_by_category: dict) -> dict:
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


@app.post("/games")
def new_game(req: NewGameRequest, uid: Optional[str] = Depends(get_optional_uid)):
    # Signed-in play vs the AI is still fully optional (no account required
    # to play at all, exactly as it's always worked) - but if the caller IS
    # signed in, tag their own color with their uid so this game attaches
    # to their account and shows up in their profile, the same way a
    # human-vs-human game already does. The AI's own "color" is left
    # uid-less - there's no account on that side to attach anything to.
    white_uid = uid if req.ai_color == "black" else None
    black_uid = uid if req.ai_color == "white" else None
    session = GameSession(ai_color=req.ai_color, ai_difficulty=req.ai_difficulty,
                           white_uid=white_uid, black_uid=black_uid)
    GAMES[session.id] = session
    game_records.save_game_record(session, ai_difficulty=req.ai_difficulty)
    return session.to_dict()


@app.get("/games/{game_id}")
def get_game(game_id: str):
    return get_view(game_id).to_dict()


@app.get("/games/{game_id}/history/{index}")
def history_at(game_id: str, index: int):
    """Read-only snapshot of the position after `index` half-moves (0 =
    the start, len(history) = the live position) - for stepping through a
    finished or in-progress game without touching its actual live state.
    Works the same whether the game is still live in memory or only
    survives as a persisted record (see get_view)."""
    view = get_view(game_id)
    try:
        return view.state_at(index)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/profile/games")
def list_my_games(uid: str = Depends(get_current_uid)):
    """Every human-vs-human game this account has played, most recently
    updated first - the data behind the Profile page's game list."""
    return game_records.list_games_for_uid(uid)


class BioRequest(BaseModel):
    bio: str


@app.post("/profile/bio")
def update_bio(req: BioRequest, uid: str = Depends(get_current_uid)):
    return accounts.update_bio(uid, req.bio)


@app.get("/games/{game_id}/legal_moves")
def legal_moves(game_id: str, col: int, row: int):
    session = get_session(game_id)
    return {"destinations": session.legal_moves(col, row)}


@app.get("/games/{game_id}/cast_moves")
def cast_moves(game_id: str):
    session = get_session(game_id)
    return _serialize_cast_moves(session.legal_cast_moves())


@app.post("/games/{game_id}/move")
def make_move(game_id: str, req: NormalMoveRequest, uid: Optional[str] = Depends(get_optional_uid)):
    session = get_session(game_id)
    _authorize_mover(session, uid)
    try:
        notation = session.apply_normal_move(req.from_col, req.from_row, req.to_col, req.to_row)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    game_records.save_game_record(session)
    state = session.to_dict()
    state["notation"] = notation
    return state


@app.post("/games/{game_id}/cast_move")
def make_cast_move(game_id: str, req: CastMoveRequest, uid: Optional[str] = Depends(get_optional_uid)):
    session = get_session(game_id)
    _authorize_mover(session, uid)
    try:
        notation = session.apply_cast_move(req.category, req.index)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    game_records.save_game_record(session)
    state = session.to_dict()
    state["notation"] = notation
    return state


@app.post("/games/{game_id}/cast_combo_destinations")
def cast_combo_destinations(game_id: str, req: CastComboDestinationsRequest):
    """Legal destinations for a SPECIFIC combo of cards the player picked
    (as opposed to /cast_moves, which only ever reflects whichever one
    combo the engine's own search happened to find first) - see
    GameSession.legal_cast_destinations_for_combo for why this exists."""
    session = get_session(game_id)
    card_specs = [c.model_dump() for c in req.cards]
    try:
        destinations = session.legal_cast_destinations_for_combo(card_specs, req.kind)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize_cast_moves(destinations)


@app.post("/games/{game_id}/cast_combo_move")
def cast_combo_move(game_id: str, req: CastComboMoveRequest, uid: Optional[str] = Depends(get_optional_uid)):
    session = get_session(game_id)
    _authorize_mover(session, uid)
    card_specs = [c.model_dump() for c in req.cards]
    try:
        notation = session.apply_cast_combo_move(card_specs, req.kind, req.to_col, req.to_row)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    game_records.save_game_record(session)
    state = session.to_dict()
    state["notation"] = notation
    return state


@app.post("/games/{game_id}/ai_move")
def ai_move(game_id: str):
    session = get_session(game_id)
    try:
        notation = session.request_ai_move()
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    game_records.save_game_record(session)
    state = session.to_dict()
    state["notation"] = notation
    return state


# -- ending a game (resign / draw) ---------------------------------------

class DrawResponseRequest(BaseModel):
    accept: bool


@app.post("/games/{game_id}/resign")
def resign(game_id: str, uid: Optional[str] = Depends(get_optional_uid)):
    session = get_session(game_id)
    color = _resigning_color(session, uid)
    try:
        session.resign(color)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    game_records.save_game_record(session)
    return session.to_dict()


@app.post("/games/{game_id}/offer_draw")
def offer_draw(game_id: str, uid: str = Depends(get_current_uid)):
    session = get_session(game_id)
    color = _participant_color(session, uid)
    try:
        session.offer_draw(color)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return session.to_dict()


@app.post("/games/{game_id}/respond_draw")
def respond_draw(game_id: str, req: DrawResponseRequest, uid: str = Depends(get_current_uid)):
    session = get_session(game_id)
    color = _participant_color(session, uid)
    try:
        session.respond_draw(color, req.accept)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    game_records.save_game_record(session)  # only meaningful on accept, but harmless either way
    return session.to_dict()
