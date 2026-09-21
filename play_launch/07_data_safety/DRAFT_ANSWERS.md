# Data safety form - DRAFT answers (built from a code audit, 2026-09-21)

Sources checked: server/accounts.py, friends.py, messages.py, chat.py, game_records.py,
notifications.py, account_deletion.py, app.py; web/js/firebase.js, profile.html;
AndroidManifest.xml; android_app/package.json; web/legal.html.
Category names below are from memory of Play's form - match them to the live form when filling it in.

## Facts from the code
- Sign-in: Firebase Auth email + password only (no Google/social sign-in, no anonymous).
- Firestore-free: data lives in Firebase Realtime DB + Firebase Storage (avatars/{uid}).
- Stored per user: uid, username, created_at, optional country (self-picked code, NOT device
  location), optional bio + avatar image, rating + rating_history, badges, friends list,
  friend requests, challenges, game_records/user_games (moves, results), in-game chat, DMs.
- Emails sent via Resend (server-side, to the user's own email): verification, friend request,
  challenge, new-DM notifications. Sender = RampartChess domain.
- API hosted on Fly.io, front end on Cloudflare Pages; both process requests (IP addresses are
  seen transiently; slowapi uses the IP for rate limiting - not stored by our code).
- Android manifest permissions: INTERNET only. No location, contacts, camera, mic, storage perms.
- No analytics, ads, crash reporting, or advertising ID anywhere (grep for gtag/analytics/
  admob/sentry/crashlytics/facebook = none). Third-party hosts referenced by the app: Google
  Firebase (gstatic/firebaseio) and apecrank.net (rulebook iframe on rules.html).
- vs-AI games on Android run on-device; nothing is sent for them.
- Deletion: in-app (profile page) + https://rampartchess.com/delete-account.

## Form answers (proposed)
| Question | Answer |
|---|---|
| Does the app collect or share required user data types? | Yes (collects) |
| Data encrypted in transit? | Yes (HTTPS/TLS everywhere) |
| Users can request data deletion? | Yes - in-app + web URL above |
| Follows Families policy / directed at children? | No (13+; not for kids) |

| Data type (Play category) | Collected | Shared* | Required/Optional | Purpose |
|---|---|---|---|---|
| Email address (Personal info) | Yes | No | Required | Account management, app functionality (auth, notification emails) |
| User IDs (Personal info) - uid + username | Yes | No | Required | Account management, app functionality |
| Other personal info - country, bio | Yes | No | Optional | App functionality (profile) |
| Photos (Photos and videos) - avatar | Yes | No | Optional | App functionality (profile) |
| Messages (In-app messages) - in-game chat + DMs | Yes | No | Optional (user-generated) | App functionality |
| App activity - game history, ratings, badges, friends | Yes | No | Required for online play | App functionality |
| Location, contacts, financial, health, web history, device IDs, audio, files, calendar | No | - | - | - |

*"Shared" in Play's definition excludes service providers acting on our behalf (Firebase/Google,
Resend, Fly.io, Cloudflare) - all processing only. Profile info shown to other players is
in-app user-to-user display, which Play does not count as third-party sharing. Re-check this
reading against the live form's help text before submitting.

## Content rating + declarations (draft)
- Has user-to-user communication (chat, DMs, friends) => answer YES to UGC/interaction questions;
  expect a rating like Teen/PEGI 12 range, not lower. Needs a reporting/blocking story: CHECK
  whether the app has a way to report/block abusive users - Play's UGC policy expects one.
- No ads, no in-app purchases, no gambling, no violence beyond abstract chess captures.
- Target audience: 13+ (matches the privacy policy). Do not opt into Families.
- Government / news / health / COVID / financial-features declarations: No.
- Advertising ID: not used (say No; no permission declared).

## PRIVACY POLICY (web/legal.html) MUST BE FIXED BEFORE SUBMISSION
Google cross-checks the form against the policy; these statements are currently wrong/missing:
1. "No other third-party services currently have access to your data" - FALSE: Resend receives
   users' email addresses and message/challenge notification content; Fly.io and Cloudflare host
   the API/site. List them as service providers.
2. No mention of notification emails (verification, friend request, challenge, new DM) or how
   to stop them.
3. Country field and badges are not mentioned under "What we collect".
4. Nothing about retention or deletion in the Privacy Policy section itself - link
   https://rampartchess.com/delete-account and say what is deleted vs anonymized
   (finished human games are kept but the user is shown as "Deleted user").
5. IP addresses are seen transiently for rate limiting - mention.
6. Age: says not directed at under-13; the Play audience declaration will say 13+ - align
   (state 13+ explicitly).
7. rules.html embeds apecrank.net (owned by the developer) - fine, but say so if it sets no
   cookies/tracking.
No edit made yet - needs the owner's OK since it is live legal text.

## UPDATE 2026-09-21
- Report/block now exists (see 09_cleanup/NOTES.md) and legal.html/delete-account.html were updated for it and
  for the earlier policy gaps. Additional data now stored: reports (reporter, reported player, reason, note, copied
  messages/profile text) and block lists. Add to Data safety: these fall under existing categories (Messages /
  Other user-generated content / App activity); purpose = App functionality + Fraud prevention, security and compliance.
- NEW FINDING: DB rules let any signed-in user read/write everything directly - see 09_cleanup/DATABASE_RULES_FINDING.md.
  Privacy-policy claim "DMs only readable by the two people" is only true after that is fixed. Do this before launch.

## Open questions for the owner
- Report/block abusive users: grep of web/js (messages/profile) found NO report or block feature - only Remove friend. Play's UGC policy expects in-app reporting + a way to block/remove abusive users; user-set avatars/bios/usernames/chat are public UGC. LIKELY REVIEW RISK - decide on a minimal report+block feature (see 09_cleanup).
- Is the DM/chat text moderated or filtered at all?
- OK to edit legal.html per the list above (I'd prepare the diff for review)?
