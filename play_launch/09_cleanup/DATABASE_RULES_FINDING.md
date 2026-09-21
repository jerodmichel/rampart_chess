# Finding: the Realtime Database rules let ANY signed-in user read/write EVERYTHING

Current rules (io_src_dev/database.rules.json - the copy of what is pasted in the Firebase console):

    ".read": "auth != null",  ".write": "auth != null"

That means anyone who can create an account (sign-up is open) can take their own Firebase ID token and
call the database's REST/SDK endpoint directly at
https://rampart-bea61-default-rtdb.firebaseio.com/ - bypassing our API entirely - and READ or WRITE:
direct messages (`dm_threads`, `user_threads`), friend lists, game records, ratings, badges, usernames,
challenges, and (new) `blocks` / `reports`. They could also overwrite other players' ratings or profiles.

Our server is NOT affected by rules (the Admin SDK bypasses them) - so tightening them cannot break
the website or the Android app, which never touch the Realtime Database directly (only Firebase Auth +
Storage; verified: web/js/firebase.js has no database imports).

## Why it matters for Google Play
- The privacy policy says direct messages are "only ever readable by the two people in that conversation".
  With these rules that is not technically true. Data safety answers must not overstate protection.
- It is the single easiest way for a malicious user to abuse the app.

## Proposed fix (play_launch/09_cleanup/database.rules.PROPOSED.json)
Deny everything by default; keep client access ONLY for the paths the legacy PyGame desktop client
(io_src_dev/) actually uses directly: `games` (which holds moves/chat/heartbeats/rematch) and
`pin_mappings`. Keep the two .indexOn blocks the server needs.

## To apply (owner, ~2 minutes, easy to undo)
1. Firebase console -> Realtime Database -> Rules. COPY the current rules somewhere first.
2. Paste the proposed JSON, click Publish.
3. Test: sign in on rampartchess.com, play a vs-AI game, open Messages, send a DM, view a profile,
   upload an avatar (that is Storage - separate rules, see below), challenge a friend.
   If the legacy desktop client is still in use, test an online game from it.
4. If anything breaks, paste the old rules back (Rules tab also has version history).

## Also check: Firebase STORAGE rules (avatars)
The web client uploads avatars straight to Storage (`avatars/{uid}`). Rules are not in the repo. In the
console (Storage -> Rules) confirm: read allowed (avatars are public), write only when
`request.auth.uid == uid`, and a size/content-type limit, e.g.
`allow write: if request.auth.uid == uid && request.resource.size < 2 * 1024 * 1024 && request.resource.contentType.matches('image/.*');`

## Baseline measured 2026-09-21 (before the change) - throwaway signed-in user, direct REST calls, counts only
READ status 200 on: dm_threads (2 keys), user_threads (3), users (7), usernames (7), friends (5), game_records (33),
game_chat (15), reports, blocks, games (389), pin_mappings (382). WRITE to a scratch path: 200.
=> any account could read every DM thread and overwrite anything. (Script: scratchpad db_probe.py - reads key COUNTS
only, writes only a scratch node it deletes.) Expected AFTER publishing the proposed rules: 401 "Permission denied"
on everything except `games` and `pin_mappings` (kept open to signed-in users for the legacy desktop client), and the
scratch write denied.

## Legacy desktop client audit (io_src_dev): touches ONLY games/{id}/{moves,chat,heartbeats,rematch} and pin_mappings/{pin}
-> both stay `auth != null` in the proposed rules, so the desktop client keeps working. Everything else is denied to
clients; the server (Admin SDK) is unaffected by rules.

## RESULT - rules published 2026-09-21 (owner saved the previous rules first)
After publishing: direct REST reads as an ordinary signed-in user -> 401 on dm_threads, user_threads, users, usernames, friends,
game_records, game_chat, reports, blocks; 200 only on games (389) and pin_mappings (382) as intended; scratch write -> 401.
Live API smoke test (throwaway account, api.rampartchess.com): 17/17 passed - me, profiles, friends, messages inbox, challenges,
blocks, live games, bio write, new vs-AI game, move, ai_move, resign, badges, rating history; stranger resign -> 403.
Repo copy io_src_dev/database.rules.json now matches what is live (uncommitted). Probe account deleted.
STILL TO DO: Firebase STORAGE rules check (avatars) - owner to paste current rules for review.
