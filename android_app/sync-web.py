#!/usr/bin/env python3
"""Populates www/ and src/main/python/ from their real sources before
every Capacitor build/sync. Both are generated, never edited directly -
re-run this any time web/, io_src_dev_ai/, server/game_session.py, or
this dir's own mobile_bridge.py changes.

--- www/ (web/js UI) ---
Only difference from a straight copy: every .html file gets one inline
classic <script> injected right after <head>, forcing api.js's BASE_URL to
the tunnel's API host - used only for human-vs-human/social features that
inherently need a server. This can't be done to web/'s own index.html etc.
directly (that file is shared with real browser testing, where the
hostname-based auto-detect in api.js must stay in charge) - Capacitor's
bundled pages run from a `capacitor://localhost` origin, which doesn't
match either of api.js's hostname checks and would otherwise silently fall
back to its http://localhost:8080 default, which means nothing inside the
packaged app.

--- src/main/python/ (on-device AI engine, via Chaquopy) ---
The same headless module subset server/Dockerfile already carves out of
io_src_dev_ai for the same reason (no pygame-display/rendering code, no
desktop-only main.py/game.py), plus server/game_session.py (confirmed
free of any FastAPI/Firebase coupling - pure stdlib + these modules) and
this dir's own mobile_bridge.py. One real patch: clicker.py does a
top-level `import pygame` that's dead code in the actual game/AI call path
(confirmed - nothing under it is reachable without pygame's own event
loop) but still executes as an import side effect of board.py needing
Clicker - pygame has no real Android wheel, so that one line is stripped
from this copy only. io_src_dev_ai/clicker.py itself (desktop/server) is
never touched.
"""
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
WEB_SRC = REPO_ROOT / "web"
ENGINE_SRC = REPO_ROOT / "io_src_dev_ai"
HERE = Path(__file__).parent
WWW_DST = HERE / "www"
PYTHON_DST = HERE / "android" / "app" / "src" / "main" / "python"

# Production API (Fly.io, see fly.toml at the repo root). For testing
# against the dev tunnel instead, temporarily use
# "https://test-api.rampartchess.com" and rebuild.
API_BASE = "https://api.rampartchess.com"
INJECT = f'<script>window.RAMPART_API_BASE="{API_BASE}";</script>'

EXCLUDE_NAMES = {"serve_dev.py", "README.md"}

ENGINE_FILES = [
    "const.py", "board.py", "square.py", "piece.py", "card.py", "grave.py",
    "clicker.py", "player.py", "move.py", "cast_move.py", "cast_button.py",
    "comprehensiveCastCache.py", "ai_engine.py", "ai_casting.py",
    "rampartbitboard.py", "rampartmovegenerator.py",
]


def sync_web():
    if WWW_DST.exists():
        shutil.rmtree(WWW_DST)
    shutil.copytree(WEB_SRC, WWW_DST, ignore=shutil.ignore_patterns(*EXCLUDE_NAMES))

    patched = 0
    for html_file in WWW_DST.rglob("*.html"):
        text = html_file.read_text()
        new_text, n = re.subn(r"(<head>)", r"\1\n" + INJECT, text, count=1)
        if n:
            html_file.write_text(new_text)
            patched += 1
        else:
            print(f"WARNING: no <head> found to patch in {html_file}")
    print(f"Synced web/ -> www/, patched {patched} html file(s) with RAMPART_API_BASE override.")


def sync_python():
    if PYTHON_DST.exists():
        shutil.rmtree(PYTHON_DST)
    PYTHON_DST.mkdir(parents=True)

    for name in ENGINE_FILES:
        shutil.copy2(ENGINE_SRC / name, PYTHON_DST / name)

    clicker_path = PYTHON_DST / "clicker.py"
    text = clicker_path.read_text()
    new_text, n = re.subn(r"^import pygame\n", "", text, count=1, flags=re.MULTILINE)
    if n != 1:
        raise RuntimeError("expected exactly one 'import pygame' line in clicker.py - check it still matches")
    clicker_path.write_text(new_text)

    # board.py's in_check() - called on every candidate-move legality check,
    # so extremely hot - unconditionally appends to a debug_trace.txt file
    # on every single call. That's leftover debug code, live on every
    # platform today (not mobile-specific), but it's a hard Chaquopy
    # crasher here (Android's asset filesystem is read-only), so it's
    # stripped from this copy regardless of whether the desktop/server copy
    # ever gets cleaned up too.
    board_path = PYTHON_DST / "board.py"
    text = board_path.read_text()
    new_text, n = re.subn(
        r"        # Also log to file:\n"
        r"        with open\('debug_trace\.txt', 'a'\) as f:\n"
        r"            f\.write\(f\"\\n=== IN_CHECK CALLED ===\\n\"\)\n"
        r"            f\.write\(f\"Piece: \{piece\.color\} \{piece\.name\}\\n\"\)\n"
        r"            f\.write\(f\"Move: \(\{move\.initial\.col\},\{move\.initial\.row\}\) -> \(\{move\.final\.col\},\{move\.final\.row\}\)\\n\"\)\n"
        r"        \n",
        "", text, count=1,
    )
    if n != 1:
        raise RuntimeError("expected exactly one debug_trace.txt block in board.py's in_check() - check it still matches")
    board_path.write_text(new_text)

    game_session_path = PYTHON_DST / "game_session.py"
    shutil.copy2(REPO_ROOT / "server" / "game_session.py", game_session_path)
    text = game_session_path.read_text()
    # game_session.py normally lives in server/ next to a sibling
    # io_src_dev_ai/ dir and inserts that into sys.path to import from it -
    # irrelevant here since every module sits flat together in this bundle
    # (already on Chaquopy's default import path), and actively breaks
    # under Chaquopy's asset-based importer, which throws FileNotFoundError
    # for a sys.path entry that doesn't exist as a real directory.
    new_text, n = re.subn(
        r'IO_SRC_DEV_AI = .*\nif IO_SRC_DEV_AI not in sys\.path:\n    sys\.path\.insert\(0, IO_SRC_DEV_AI\)\n\n',
        "", text, count=1,
    )
    if n != 1:
        raise RuntimeError("expected exactly one IO_SRC_DEV_AI sys.path block in game_session.py - check it still matches")
    game_session_path.write_text(new_text)

    shutil.copy2(HERE / "mobile_bridge.py", PYTHON_DST / "mobile_bridge.py")

    print(f"Synced {len(ENGINE_FILES)} engine file(s) + game_session.py + mobile_bridge.py -> "
          f"{PYTHON_DST.relative_to(REPO_ROOT)}, stripped clicker.py's dead pygame import.")


def cap_sync():
    """Copies www/ into the actual Android assets Gradle bundles into the
    APK (android/app/src/main/assets/public) - a real bug hit once already:
    without this, `gradlew assembleDebug` silently packages whatever web/js
    was there from the last `cap sync`, no error, no warning, whether or
    not this script's own www/ output just changed. Doing it here (rather
    than trusting every caller to remember a separate `npx cap sync
    android`) makes that class of mistake impossible."""
    subprocess.run(["npx", "cap", "sync", "android"], cwd=HERE, check=True)


def main():
    sync_web()
    sync_python()
    cap_sync()


if __name__ == "__main__":
    main()
