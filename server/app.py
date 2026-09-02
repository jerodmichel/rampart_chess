"""Minimal HTTP API wrapping the Rampart game/AI logic in io_src_dev_ai, for
a future browser client. This is step 1 of the browser port: prove the
existing Python rules engine + AI can run headless behind an API, before any
JS/rendering work happens. In-memory game storage only for now (fine for
local testing; a real deployment would move this to Firestore so state
survives across Cloud Run instances/restarts)."""

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game_session import GameSession, IllegalMoveError

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
    session = GAMES.get(game_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"no game with id {game_id}")
    return session


class NewGameRequest(BaseModel):
    ai_color: str = "black"
    ai_difficulty: str = "Medium"


class NormalMoveRequest(BaseModel):
    from_col: int
    from_row: int
    to_col: int
    to_row: int


class CastMoveRequest(BaseModel):
    category: str  # 'strike' | 'raise_raider' | 'raise_queen'
    index: int


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
def new_game(req: NewGameRequest):
    session = GameSession(ai_color=req.ai_color, ai_difficulty=req.ai_difficulty)
    GAMES[session.id] = session
    return session.to_dict()


@app.get("/games/{game_id}")
def get_game(game_id: str):
    return get_session(game_id).to_dict()


@app.get("/games/{game_id}/legal_moves")
def legal_moves(game_id: str, col: int, row: int):
    session = get_session(game_id)
    return {"destinations": session.legal_moves(col, row)}


@app.get("/games/{game_id}/cast_moves")
def cast_moves(game_id: str):
    session = get_session(game_id)
    return _serialize_cast_moves(session.legal_cast_moves())


@app.post("/games/{game_id}/move")
def make_move(game_id: str, req: NormalMoveRequest):
    session = get_session(game_id)
    try:
        notation = session.apply_normal_move(req.from_col, req.from_row, req.to_col, req.to_row)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    state = session.to_dict()
    state["notation"] = notation
    return state


@app.post("/games/{game_id}/cast_move")
def make_cast_move(game_id: str, req: CastMoveRequest):
    session = get_session(game_id)
    try:
        notation = session.apply_cast_move(req.category, req.index)
    except IllegalMoveError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    state = session.to_dict()
    state["notation"] = notation
    return state
