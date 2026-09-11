# Rampart - Browser Client (v0)

Plain JS + Canvas frontend for the `server/` FastAPI backend. No build step,
no framework, no bundler - open `index.html` through a local static server
and it talks to the API over `fetch`.

Scope of this first pass: single-player vs the AI, matching what `server/`
already supports. Human-vs-human browser multiplayer is a later phase.

A square-tile variant of this client's *first* pass (before this layout was
matched to the desktop client's real proportions) is preserved in `../mobile/`
as a starting point for a future compact/touch build - see that directory's
own copy of this README for what it currently is (a frozen snapshot, not yet
under active development).

## Running it locally

You need two things running at once: the API backend, and a static file
server for this directory (browsers block ES module imports over `file://`).

**1. Start the backend** (from the repo root):

```bash
cd server
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

**2. Serve this directory** (from `web/`, in another terminal - not the repo
root, or you'll get a directory listing instead of the game):

```bash
cd web
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
- Click-to-move for normal chess-like moves - legal destinations shown as
  dots, or a chess.com-style bracket-cornered ring when the destination
  would capture a piece
- Casting, matching the desktop client's actual manual card-selection flow:
  click deck cards (once you've infiltrated the enemy jack house) and board
  cards to build a combo, then STRIKE/RAISE. Since the server's own combo
  search (`_find_valid_combo`) only ever finds one combo per category and
  can't confirm a *specific* hand, casting goes through
  `/cast_combo_destinations` and `/cast_combo_move`, which validate your
  exact selected cards via `calc_cast_moves(..., known_combo=...)` - the
  same mechanism the desktop client uses - rather than matching against a
  generic precomputed list. Valid destinations for a committed combo are
  shown as magenta dots, matching the move-dot style.
- One canvas at the same 1000x860 design resolution, rectangular cell
  proportions (80x133), colors, card-square labels, deck panels, graveyard,
  and STRIKE/RAISE button styling/position as the pygame client - ported
  directly from `io_src_dev_ai`'s `const.py`/`theme.py`/`game.py` draw calls
  (see `js/constants.js`, `js/render.js`), including its Cinzel button font.
- Theme (4 color sets) and piece-style (2 sets - "New" has no bishop art,
  same as the desktop client, so bishop always renders from "Default"
  regardless of which is selected) switchers in the header.
- AI turn handling (auto-triggers `/ai_move` and shows a "thinking" status
  in the same on-canvas prompt spot the desktop client uses)

## What's not here yet

- Board flipping / perspective toggle
- Sound, animations, cemetery-emblem switching (the emblem itself renders;
  cycling between alternates like the desktop's `Y` key doesn't yet)
- Move history viewer, save/load, rematch, chat
- A responsive/compact layout for phones - that's `../mobile/`'s job, kept
  deliberately separate so this client can stay a faithful match to the
  desktop proportions without fighting a second set of requirements
- Login/profiles/avatars/ratings, and persisting games to an account so
  they can be reviewed later - the actual "platform" layer this is a first
  step toward
