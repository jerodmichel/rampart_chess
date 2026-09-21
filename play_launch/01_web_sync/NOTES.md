# Sync web/ and the engine into the Android project

Status: DONE 2026-09-21 (sync + cap sync run; awaiting user commit of android_app/www)

Why: android_app/www is stale (web/ has ~18 changed files since the last sync,
including the mobile console/balloon fix).

Steps
- [x] `python3 android_app/sync-web.py`  (regenerates android_app/www and
      android_app/android/app/src/main/python from web/, io_src_dev_ai/,
      server/game_session.py; injects RAMPART_API_BASE=https://api.rampartchess.com)
- [x] `cd android_app && npx cap sync android`
- [x] Confirm www/ pages contain the API_BASE override and today's main.js changes
- [ ] Commit the regenerated www/ (it is tracked)

Done when: www/js/main.js matches web/js/main.js and API base is the live API.

Log
- 2026-09-21: synced 8 html + js/css; API base = https://api.rampartchess.com; www/js/main.js identical to web/js/main.js (includes scroll fix + fitPromptFontSize). Newly added to www: js/taplabel.js, verify.html. Not yet committed.
