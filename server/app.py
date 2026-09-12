"""Minimal HTTP API wrapping the Rampart game/AI logic in io_src_dev_ai, for
a future browser client. This is step 1 of the browser port: prove the
existing Python rules engine + AI can run headless behind an API, before any
JS/rendering work happens. In-memory game storage only for now (fine for
local testing; a real deployment would move this to Firestore so state
survives across Cloud Run instances/restarts)."""

import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

import accounts
import badges
import chat
import challenges
import friends
import game_records
import messages
import ratings
from firebase_auth import get_current_uid, get_optional_uid
from game_session import GameSession, IllegalMoveError, ReplayOnlyGame

app = FastAPI(title="Rampart API")

# Was allow_origins=["*"] - fine while this only ever talked to a
# same-machine dev server, not once real strangers can reach it. No real
# domain exists yet (see project-rampart-browser-port memory), so this
# defaults to the local dev ports web/ actually gets served from
# (python -m http.server / VS Code Live Server's usual picks); set
# ALLOWED_ORIGINS (comma-separated) to override once there's a real one -
# zero code changes needed at that point.
_DEFAULT_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080,http://127.0.0.1:8080"
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-IP rate limiting (in-memory - fine for a single server instance,
# same scale assumption as the in-memory GAMES dict below) on the
# endpoints most worth throttling: account creation, chat, challenges, and
# starting a new game (the last one because an anonymous vs-AI game is
# free to spam and each one spins up a real search). Read-only endpoints
# (legal_moves, GET /games/{id}, etc.) are left unlimited.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
    """Unlike a move, resigning (or aborting - see /abort below) isn't
    gated by whose turn it is - either participant can act at any time. An
    AI game has exactly one human (whichever color isn't the AI's), so no
    account is needed to identify who's acting there, same as the rest of
    that mode."""
    if session.ai_color is not None:
        return "black" if session.ai_color == "white" else "white"
    if uid == session.white_uid:
        return "white"
    if uid == session.black_uid:
        return "black"
    raise HTTPException(status_code=403, detail="you are not a participant in this game")


def _finalize_if_needed(session: GameSession) -> None:
    """Idempotent - the first time (and only the first time) a session is
    observed to be over, persists its final game_records entry and applies
    Elo changes (human-vs-human games only). Called after every mutating
    endpoint's routine save AND from GET /games/{id}, because a TIMEOUT
    ending is only ever discovered lazily via to_dict()'s _check_timeout()
    - every mutating endpoint already refuses to act once is_game_over()
    is true, so without also checking here on a mere read, a timeout's
    final record/rating update would never happen at all. The extra
    game_records.save_game_record call on the exact move/read that ends a
    non-timeout game is redundant but harmless - that function overwrites
    the record with the same data either way."""
    if not session.is_game_over() or getattr(session, "_finalized", False):
        return
    session._finalized = True
    game_records.save_game_record(session)
    if session.white_uid and session.black_uid:
        pre_white = ratings.get_rating_state(session.white_uid)
        pre_black = ratings.get_rating_state(session.black_uid)
        ratings.apply_game_result(session)
        badges.check_and_award(session, pre_white["rating"], pre_black["rating"])


def _participant_color(session: GameSession, uid: Optional[str]) -> str:
    """Shared by anything that only makes sense between two real opponents
    (draw offers, chat) - there's no one for an AI to negotiate or chat
    with."""
    if session.white_uid is None and session.black_uid is None:
        raise HTTPException(status_code=400, detail="this game has no human opponent")
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
@limiter.limit("5/minute")
def register(request: Request, req: RegisterRequest, uid: str = Depends(get_current_uid)):
    return accounts.register_username(uid, req.username)


@app.get("/auth/me")
def get_me(uid: str = Depends(get_current_uid)):
    return accounts.get_profile(uid)


@app.get("/auth/users/{username}")
def find_user(username: str, uid: str = Depends(get_current_uid)):
    """Resolves a username to a uid, for challenging/matching a player by
    name instead of sharing a game id."""
    return {"username": username, "uid": accounts.lookup_uid(username)}


# -- public player profiles ----------------------------------------------
#
# Distinct from /auth/me (always the caller's own account) and
# /auth/users/{username} (auth-required, uid-only, for challenge targeting)
# - these are for viewing SOMEONE ELSE's stats/history, so no sign-in is
# required and nothing sensitive is exposed (accounts.get_profile never
# stores email/etc. at all - that's Firebase Auth's own concern).

@app.get("/players/{username}")
def get_player_profile(username: str):
    return accounts.get_profile(accounts.lookup_uid(username))


@app.get("/players/{username}/games")
def get_player_games(username: str):
    """Every human-vs-human/persisted game this account has played - same
    data /profile/games returns for your own account, just reachable by
    username instead of requiring you to BE that account."""
    return game_records.list_games_for_uid(accounts.lookup_uid(username))


@app.get("/players/{username}/rating_history")
def get_player_rating_history(username: str):
    """Every rated-game rating snapshot for this account, oldest first -
    the data behind the Stats page's Rating Timeline chart. Date-range
    filtering (Last 30 Days / 6 Months / All Time) happens client-side on
    this same list rather than as separate query params - the dataset per
    player is small enough that there's no reason to make three round trips
    instead of one."""
    return ratings.get_rating_history(accounts.lookup_uid(username))


@app.get("/players/{username}/rank")
def get_player_rank(username: str):
    return ratings.get_rank(accounts.lookup_uid(username))


@app.get("/players/{username}/badges")
def get_player_badges(username: str):
    """{badge_id: {unlocked_at}} for every badge this account has earned -
    see badges.py for what's checked and when. Phase 1: Ladder Trophies,
    Tenure Badges, Giant Slayer, Kingslayer, Blitzkrieg."""
    return badges.get_badges(accounts.lookup_uid(username))


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
@limiter.limit("10/minute")
def create_challenge(request: Request, req: ChallengeRequest, uid: str = Depends(get_current_uid)):
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
                           time_control=record.get("time_control"),
                           white_username=white_username, black_username=black_username)
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


@app.get("/games/live")
def list_live_games():
    """Public spectator list - every in-memory, still-in-progress
    human-vs-human game. AI games are excluded (no second human to watch
    against) and so is anything already over. Each id opens read-only in
    the exact same board view a finished game's ledger link already uses -
    GameSession/main.js don't care who's looking, only whether the
    viewer's own uid happens to match a color (see humanColor() in
    main.js), so no separate "spectator mode" was needed."""
    out = []
    for session in GAMES.values():
        if session.ai_color is not None or session.is_game_over():
            continue
        out.append({
            "id": session.id,
            "white_username": accounts.get_profile(session.white_uid)["username"],
            "black_username": accounts.get_profile(session.black_uid)["username"],
            "time_control": session.time_control,
        })
    return out


@app.post("/games")
@limiter.limit("10/minute")
def new_game(request: Request, req: NewGameRequest, uid: Optional[str] = Depends(get_optional_uid)):
    # Signed-in play vs the AI is still fully optional (no account required
    # to play at all, exactly as it's always worked) - but if the caller IS
    # signed in, tag their own color with their uid so this game attaches
    # to their account and shows up in their profile, the same way a
    # human-vs-human game already does. The AI's own "color" is left
    # uid-less - there's no account on that side to attach anything to.
    white_uid = uid if req.ai_color == "black" else None
    black_uid = uid if req.ai_color == "white" else None
    human_username = accounts.get_profile(uid)["username"] if uid else None
    white_username = human_username if req.ai_color == "black" else None
    black_username = human_username if req.ai_color == "white" else None
    session = GameSession(ai_color=req.ai_color, ai_difficulty=req.ai_difficulty,
                           white_uid=white_uid, black_uid=black_uid,
                           white_username=white_username, black_username=black_username)
    GAMES[session.id] = session
    game_records.save_game_record(session, ai_difficulty=req.ai_difficulty)
    return session.to_dict()


@app.get("/games/{game_id}")
def get_game(game_id: str):
    view = get_view(game_id)
    state = view.to_dict()
    if isinstance(view, GameSession):
        _finalize_if_needed(view)
    return state


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


class CountryRequest(BaseModel):
    country: str  # ISO code (e.g. 'US') or an extinct-state code (e.g. 'USSR') - empty string clears it


@app.post("/profile/country")
def update_profile_country(req: CountryRequest, uid: str = Depends(get_current_uid)):
    return accounts.update_country(uid, req.country.upper())


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
    _finalize_if_needed(session)
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
    _finalize_if_needed(session)
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
    _finalize_if_needed(session)
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
    _finalize_if_needed(session)
    return session.to_dict()


@app.post("/games/{game_id}/abort")
def abort_game(game_id: str, uid: Optional[str] = Depends(get_optional_uid)):
    """Only valid before a single move has been made - lets either
    participant walk away from a game that hasn't really started, without
    it counting as a resignation (a loss) or being saved anywhere. Unlike
    every other mutating endpoint, this doesn't call save_game_record - it
    deletes the session outright, and any record already written at
    creation time (new_game/accept_challenge persist one immediately for a
    signed-in player) is deleted right along with it.

    Deliberately doesn't use get_session() - unlike a move or a resignation,
    aborting needs no live Board/AI state at all, only the uids and move
    count, which the persisted record already has. So unlike every other
    mutating endpoint, this still works even after a server restart drops
    the live session - unmet, a zero-move game orphaned that way could
    never be cleaned up (it'd sit forever as an unplayable "ongoing" entry
    in a ledger, since get_session's 409 blocks every other action too)."""
    session = GAMES.get(game_id)
    if session is not None:
        _resigning_color(session, uid)  # just to check the caller is a participant
        if session.move_log:
            raise HTTPException(status_code=400, detail="can't abort a game once a move has been made")
        if session.is_game_over():
            raise HTTPException(status_code=400, detail="the game is already over")
        del GAMES[game_id]
        game_records.delete_game_record(session.id, session.white_uid, session.black_uid)
        return {"status": "aborted"}

    record = game_records.get_game_record(game_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no game with id {game_id}")
    white_uid, black_uid = record.get("white_uid"), record.get("black_uid")
    if not uid or uid not in (white_uid, black_uid):
        raise HTTPException(status_code=403, detail="you are not a participant in this game")
    if record.get("history"):
        raise HTTPException(status_code=400, detail="can't abort a game once a move has been made")
    if record.get("result"):
        raise HTTPException(status_code=400, detail="the game is already over")
    game_records.delete_game_record(game_id, white_uid, black_uid)
    return {"status": "aborted"}


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
    _finalize_if_needed(session)
    return session.to_dict()


# -- chat -----------------------------------------------------------------
#
# Participant-only, same as offer_draw/respond_draw above - _participant_color
# raises for either an AI game (no opponent to chat with) or a non-participant.

class ChatMessageRequest(BaseModel):
    text: str


@app.post("/games/{game_id}/chat")
@limiter.limit("20/minute")
def send_chat_message(request: Request, game_id: str, req: ChatMessageRequest, uid: str = Depends(get_current_uid)):
    session = get_session(game_id)
    _participant_color(session, uid)
    profile = accounts.get_profile(uid)
    return chat.send_message(game_id, uid, profile["username"], req.text)


@app.get("/games/{game_id}/chat")
def get_chat_messages(game_id: str, uid: str = Depends(get_current_uid)):
    # get_view (not get_session) - a finished/persisted game's chat history
    # should stay readable the same way its move history does.
    session = get_view(game_id)
    _participant_color(session, uid)
    return chat.list_messages(game_id)


# -- friends --------------------------------------------------------------
#
# Same request/accept/decline/dismiss lifecycle as challenges above -
# friends.py mirrors challenges.py's shape deliberately. Requires the
# repo's database.rules.json .indexOn addition for "friend_requests" to
# actually be deployed (pasted into the console) - see that file's comment.

class FriendRequestBody(BaseModel):
    to_username: str


@app.post("/friends/request")
@limiter.limit("10/minute")
def send_friend_request(request: Request, req: FriendRequestBody, uid: str = Depends(get_current_uid)):
    profile = accounts.get_profile(uid)
    return friends.send_request(uid, profile["username"], req.to_username)


@app.get("/friends/incoming")
def list_incoming_friend_requests(uid: str = Depends(get_current_uid)):
    return friends.list_incoming(uid)


@app.get("/friends/outgoing")
def list_outgoing_friend_requests(uid: str = Depends(get_current_uid)):
    return friends.list_outgoing(uid)


@app.post("/friends/{request_id}/accept")
def accept_friend_request(request_id: str, uid: str = Depends(get_current_uid)):
    return friends.accept(request_id, uid)


@app.post("/friends/{request_id}/decline")
def decline_friend_request(request_id: str, uid: str = Depends(get_current_uid)):
    friends.decline(request_id, uid)
    return {"status": "declined"}


@app.post("/friends/{request_id}/dismiss")
def dismiss_friend_request(request_id: str, uid: str = Depends(get_current_uid)):
    friends.dismiss(request_id, uid)
    return {"status": "dismissed"}


@app.get("/friends")
def list_my_friends(uid: str = Depends(get_current_uid)):
    return friends.list_friends(uid)


@app.post("/friends/{username}/remove")
def remove_friend(username: str, uid: str = Depends(get_current_uid)):
    friends.remove_friend(uid, username)
    return {"status": "removed"}


# -- direct messages (friends only) ----------------------------------------

class DirectMessageBody(BaseModel):
    text: str


@app.post("/messages/{username}")
@limiter.limit("20/minute")
def send_direct_message(request: Request, username: str, req: DirectMessageBody,
                         uid: str = Depends(get_current_uid)):
    profile = accounts.get_profile(uid)
    return messages.send_message(uid, profile["username"], username, req.text)


@app.get("/messages/{username}")
def get_direct_messages(username: str, uid: str = Depends(get_current_uid)):
    return messages.list_messages(uid, username)


@app.get("/messages")
def get_inbox(uid: str = Depends(get_current_uid)):
    return messages.list_inbox(uid)
