# Plan: minimal Report + Block (Play UGC policy) - PROPOSAL, no code written yet

## Why
Play's User Generated Content policy expects apps with user-to-user content to provide (a) in-app
reporting of abusive content/users, (b) a way to block users, (c) moderation that can act on reports,
and (d) terms that prohibit abuse. Today we have (d) (Terms > Conduct) and "Remove friend" only.
Public UGC in the app: username, bio, avatar image, in-game chat, DMs (friends only), friend requests,
challenges.

## Smallest thing that satisfies it
### Server (server/app.py + new server/moderation.py)
- `POST /report`  body {target_username, kind: profile|chat|dm|other, game_id?/thread_id?, reason (enum:
  harassment|hate|spam|inappropriate_image|cheating|other), details (<=500 chars)}.
  Stores `reports/{id}` = {reporter_uid, target_uid, kind, context ids, a server-copied excerpt of the
  reported message (so it can't be edited away), reason, details, created_at, status:"open"}.
  Emails apecrank@gmail.com via the existing Resend helper (notify to a fixed address). Rate-limited
  like chat (slowapi). Cannot report yourself; max N reports/user/day.
- `POST /block/{username}` and `DELETE /block/{username}` -> `blocks/{uid}/{target_uid}: true`;
  `GET /blocks` -> list.
- Enforcement (one helper `is_blocked(a, b)` checked either direction):
  - friends.send_request / messages.send_message / challenges create: reject with a neutral 403/404
    ("can't message this user") so the blocked person isn't told they were blocked.
  - blocking an existing friend also removes the friendship (reuse remove-friend).
  - in-game chat: blocked opponent's messages hidden from the blocker (game itself can't be refused
    once started; blocker may resign).
  - notification emails from a blocked sender are suppressed.
- Account deletion (account_deletion.py): delete `blocks/{uid}` and `blocks/*/{uid}` entries. KEEP
  reports (needed for moderation) but replace reporter/target identity with tombstone where the account
  is deleted - state this in the privacy policy.

### Client (web/js/)
- Profile page of ANOTHER user: "Block" and "Report" buttons (styled like the muted Remove-friend one,
  same confirm pattern as the Messages remove-friend confirm).
- Messages thread header: "..." menu -> Report / Block.
- Game chat: long-press/tap a message -> Report (reuse taplabel.js style for touch).
- Settings/Profile: "Blocked users" list with Unblock.
- Report dialog: reason dropdown + optional details + Submit; success toast "Thanks - we'll review it."

### Moderation process (needs you, not code)
- Where reports land: email + `reports/` node. Define what you do: review within ~72h, warn/suspend/
  remove content. Need a way to suspend an account (Firebase Auth `disabled` flag via a small admin
  script - e.g. `python3 server/admin_suspend.py <username>`), and to clear a bad avatar/bio.
- Add to Terms: how to report, that you act on reports, that repeat abusers are removed.

## Effort / risk
Server ~1 file + ~5 small hooks; client ~4 UI spots; tests with fake DB (as done for account deletion)
and a pass in the mobile rig. Roughly one focused session. Server change => `fly deploy --ha=false`
(interrupts live games) and the Android www/ resync + new versionCode.
Play review may still ask questions; having this shipped before the first review is the low-risk path.

## Decisions needed from the owner
1. OK to build this (scope above), or cut anything (e.g. skip chat-message report in v1)?
2. Who receives reports (apecrank@gmail.com ok?) and what response time do you want to state?
3. Is suspending accounts via an admin script acceptable for now?
