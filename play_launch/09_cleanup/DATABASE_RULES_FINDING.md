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
