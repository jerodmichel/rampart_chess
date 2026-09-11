# Rampart - Browser Client (v0)

Plain JS + Canvas frontend for the `server/` FastAPI backend. No build step,
no framework, no bundler - open `index.html` through a local static server
and it talks to the API over `fetch`.

Scope of this first pass: single-player vs the AI, matching what `server/`
already supports. Human-vs-human browser multiplayer is a later phase.

## Running it locally

You need two things running at once: the API backend, and a static file
server for this directory (browsers block ES module imports over `file://`).

**1. Start the backend** (from the repo root):

```bash
cd server
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

**2. Serve this directory** (from `web/`, in another terminal):

```bash
python3 -m http.server 5500
```

Then open `http://localhost:5500` in a browser.

If the API isn't on `http://localhost:8080`, set it before `main.js` loads by
adding this above the module `<script>` tag in `index.html`:

```html
<script>window.RAMPART_API_BASE = 'https://your-api-host';</script>
```

## What's implemented

- New game (choose which color the AI plays, and its difficulty)
- Click-to-move for normal chess-like moves (legal destinations highlighted)
- Casting: rather than reimplementing the desktop client's manual
  card-selection UI (the source of several of the bugs fixed this session),
  the server already computes every legal Strike/Raise option up front
  (`GET /games/{id}/cast_moves`), so the client just lists them - "square,
  cards used" - and executes whichever one you click. Simpler and can't
  drift out of sync with the rules engine.
- Deck panels (used/available cards), graveyards, move history
- AI turn handling (auto-triggers `/ai_move` and shows a "thinking" status)
- Board layout/colors/card-square labels ported from `io_src_dev_ai`'s
  `const.py`/`theme.py` (see `js/constants.js`, `js/render.js`) so it reads
  the same as the desktop client

## What's not here yet

- Board flipping / perspective toggle
- Sound, animations, alternate piece sets
- Save/load, rematch, chat - all multiplayer-era features
- Mobile-specific layout (the canvas is a fixed 640x398 for now; the
  Canvas+vanilla-JS choice was made specifically so this can grow into a
  compact/touch layout later without a rewrite)
- Login/profiles/avatars/ratings - the actual "platform" layer this is a
  first step toward
