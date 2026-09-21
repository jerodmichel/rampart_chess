# Google Play launch - master checklist

One folder per box. Each has a NOTES.md (goal, steps, done-criteria, log).
Update the Status line in the folder AND tick the box here.

| # | Item | Folder | Status |
|---|------|--------|--------|
| 1 | Sync web/ + engine into Android project | 01_web_sync | [x] synced, needs commit |
| 2 | Release keystore + signing config | 02_signing | [x] done, key backed up |
| 3 | Version bump + release .aab | 03_release_build | [x] signed .aab ready (v1); bump versionCode for later uploads |
| 4 | 16KB page-size check | 04_16kb_check | [x] PASS |
| 5 | Play Console developer account | 05_play_account | [~] created; verification NOT yet submitted (needs ID) |
| 6 | Store listing text + graphics | 06_store_listing | [~] drafted - owner review |
| 7 | Data safety / content rating / declarations | 07_data_safety | [~] drafted; report/block built; DB rules HARDENED (live); Storage rules check pending |
| 8 | Internal -> closed testing -> production | 08_testing_tracks | [ ] |
| 9 | Cleanup / loose ends | 09_cleanup | [ ] |

Critical path: 5 (account verification + the closed-test waiting period) - start early.

Secrets: keystore + passwords live in ~/Documents/rampart_secrets/ (outside the repo, backed up).
Build outputs (.aab/.apk) are gitignored here. Never paste passwords into chat or notes.

## >>> WHERE WE LEFT OFF (2026-09-21, night) <<<
Everything below is committed, pushed, and deployed (Fly API + Cloudflare Pages), and verified live.

**Done today:** signed release .aab (upload key made + backed up off-machine); 16KB check PASS; privacy policy + deletion page
rewritten; store listing text + icon + feature graphic + 3 screenshots drafted (owner reviewed/edited); report + block feature
(+ owner CLI server/admin_moderation.py); authorization fix (strangers could resign/abort/advance someone's vs-AI game);
Firebase Realtime DB rules HARDENED (only games + pin_mappings open to clients; verified 401s; repo copy matches);
notification bell now shows unread DMs; x86_64 ABI kept in release (decided).

**UPDATE (2026-09-21, later): bundle REBUILT and identity verification SUBMITTED.**
- The .aab was re-synced from web/ and rebuilt; verified the bundled files match web/ (incl. unread-DM bell). versionCode is
  still 1 (fine: nothing uploaded yet; MUST increase for every later upload). Rebuild recipe if web/ changes again:
  `python3 android_app/sync-web.py` (also runs cap sync), bump versionCode in android_app/android/app/build.gradle,
  then `cd android_app/android && ./gradlew bundleRelease` -> app/build/outputs/bundle/release/app-release.aab.
  (Signing config reads ~/Documents/rampart_secrets/keystore.properties; keystore is backed up.)
- Android emulator AVD `rampart_pixel` (Pixel 6) exists; the real signed release APK was installed and runs. GOTCHA: the
  emulator WebView reports pointer:fine, so the `(pointer: coarse)` mobile CSS does not apply and the signed-out header
  looks clipped (Log In / Forgot password off-screen). NOT a real bug - with CDP touch emulation the panel fits at
  412/393/360/320 CSS px. Recipe: see the "Android emulator" note in Claude memory (reference_android_emulator_testing).

**Blocked on the OWNER (needs ID / accounts / people):**
1. ~~Submit Play Console identity verification~~ SUBMITTED 2026-09-21; waiting on Google. Critical path: closed-test clock
   can't start until verified. Runbook: 05_play_account/WHEN_ID_READY.md.
2. Collect 12-20 tester Gmail addresses (personal account => closed test ~12 testers x ~14 days; confirm numbers in Console).
   Tracker: 08_testing_tracks/NOTES.md.
3. Create a throwaway DEMO account on rampartchess.com for Google's reviewers ("App access" section).
4. Paste Firebase STORAGE rules (avatars) for review - only the DB rules are done. Want: public read, owner-only write, size/type limit.
5. Read reports occasionally: `python3 server/admin_moderation.py reports` (needs server/serviceAccountKey.json).

**Ready for me to do when asked:**
- Take real-app screenshots from the emulator (needs touch emulation kept on so the mobile layout applies).
- Review Storage rules once pasted.
- Final pre-upload checklist pass (store text vs. actual features, Data safety vs. code) - see 07_data_safety/DRAFT_ANSWERS.md.

**Loose ends / nice-to-have:** no in-app switch for notification emails (privacy policy says "email us"); android_app/node_modules is
tracked in git (~1000 files, untrack later); DMARC is p=reject (loosen if mail vanishes); live two-device human-vs-human test;
iPhone fake-fullscreen console path unverified; legacy desktop client still uses games/pin_mappings.

**How we test (reusable):** Playwright + system Chrome in the session scratchpad (npm i playwright-core; chrome at
~/.cache/ms-playwright/chromium-1243/...); local servers `cd server && python3 -m uvicorn app:app --port 8080` and
`cd web && python3 serve_dev.py 5500`; throwaway Firebase users via Admin SDK (email_verified) and delete with
account_deletion.delete_account. Gotcha: Playwright waitForFunction does NOT await async predicates - poll from Node.
Unit tests: `cd server && python3 -m unittest discover -s tests` (21, fake DB enforces .indexOn).

## Day-of runbook
05_play_account/WHEN_ID_READY.md lists the exact steps for once identity verification is possible.

## Waiting on the owner
- Review store listing text/graphics (06) and legal.html diff (07), then commit.
- Review + commit report/block (09_cleanup/NOTES.md has deploy order!) and decide on DB rules (09_cleanup/DATABASE_RULES_FINDING.md).
- Submit identity verification; recruit ~15-20 closed testers (08 tracker).
