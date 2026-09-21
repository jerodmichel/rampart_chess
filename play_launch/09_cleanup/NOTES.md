# Repo hygiene and other loose ends

Status: NOT STARTED

- [ ] android_app/node_modules is tracked in git (~1047 files): add to .gitignore
      and `git rm -r --cached android_app/node_modules`
- [ ] Live two-device human-vs-human gameplay test
- [ ] Check iPhone .fakeFullscreen console path (not Play-blocking)
- [ ] DMARC is p=reject - loosen if mail goes missing
- [ ] Consider a separate Firebase test project before bigger destructive features
- [x] BUILT 2026-09-21 (uncommitted) - UGC safety for Play policy: minimal in-app 'Report' (user/profile/chat message -> stored for review + email to support) and 'Block' (hide DMs/challenges from that user). Currently only Remove friend exists. Decide scope before first review.
- See REPORT_BLOCK_PLAN.md (proposal, awaiting owner decisions).

## Report/block - what was built (2026-09-21)
Server: server/blocks.py, server/reports.py, admin_moderation.py (owner CLI), endpoints GET/POST/DELETE /blocks, POST /report,
hooks in friends/challenges/messages/chat/account_deletion, notifications.notify_report (plain-text email to REPORT_EMAIL,
default apecrank@gmail.com). Client: web/js/moderation-ui.js (shared dialog, renders inside fullscreen), buttons on profile
(Report/Block/Unblock + own 'Blocked players' list), Messages thread (Report/Block), game chat ('Report opponent').
Policy text: web/legal.html (Conduct + collection + retention) and web/delete-account.html updated.
Tests: server/tests (14 unit tests, in-memory fake DB that enforces .indexOn like the real one) + real end-to-end run
(2 throwaway accounts, real Firebase, real Chrome incl. phone fullscreen): 28/29 automated checks passed, the 1 miss was
a check-timing race in the test, not the feature. Test data fully removed afterwards.
DEPLOY ORDER MATTERS: `fly deploy --ha=false` (server) BEFORE pushing web/ - the profile page now calls GET /blocks, so
web without the new server breaks the friend-status buttons. Then android sync-web.py + new versionCode + bundleRelease.
Owner reading reports: `python3 server/admin_moderation.py reports` (needs server/serviceAccountKey.json).
- [ ] Owner: read DATABASE_RULES_FINDING.md (any signed-in user can read/write the whole DB directly) and decide on the proposed rules.
- [ ] Owner: check Firebase Storage rules for avatars (size/type/owner-only write).

## Authorization fix: strangers could resign/abort/advance someone's vs-AI game (found by owner 2026-09-21)
Owner noticed Resign + move options appear on another user's in-progress game. Server probe confirmed: for a signed-in
player's game vs the computer, the AI's colour has no uid, so a stranger (even logged out) could POST resign / abort /
ai_move / move-on-the-AI's-turn. Human-vs-human games were already protected (403). Also the client's humanColor() treated
every viewer of a vs-AI game as the player (buttons, legal-move dots, and it auto-called ai_move when a spectator merely
opened a game on the AI's turn). FIXED (uncommitted): server/app.py _require_ai_game_owner (used by _authorize_mover,
_resigning_color/abort, ai_move); web/js/main.js humanColor() ownership check + guarded AI trigger + resume-after-profile-load.
Anonymous vs-AI games (no uid on either side) deliberately unchanged. Verified: 19 server checks (stranger / other user / owner /
anonymous) + 7 browser checks (spectator, logged-out visitor, owner resuming). Server deploy needed (same one as report/block).

## Notification bell now includes unread DMs (2026-09-21, uncommitted)
Owner asked (bell only counted friend requests + challenges; email for DMs was fine - a few minutes' delay had looked like a failure).
Server: user_threads/{uid}/{thread}.unread (True for recipient on send, False for sender), POST /messages/{username}/read,
list_inbox returns normalized `unread` (False for old threads without the field, and for threads with blocked users).
Client: header.js bell adds 'New message from X' rows (link messages.html?user=X); messages.js marks the open thread read (only
while the tab is visible). Tests: server/tests/test_unread.py (7) + browser run 11/11 (light up within the 10s poll, row link,
opening clears, live message in open thread doesn't leave bell lit, sender not alerted, reply lights the other side).
Deploy: `fly deploy --ha=false` first, then push web/. Android: re-sync + bump versionCode before next bundle.
