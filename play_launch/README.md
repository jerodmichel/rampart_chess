# Google Play launch - master checklist

One folder per box. Each has a NOTES.md (goal, steps, done-criteria, log).
Update the Status line in the folder AND tick the box here.

| # | Item | Folder | Status |
|---|------|--------|--------|
| 1 | Sync web/ + engine into Android project | 01_web_sync | [x] synced, needs commit |
| 2 | Release keystore + signing config | 02_signing | [x] done, key backed up |
| 3 | Version bump + release .aab | 03_release_build | [~] first .aab built; ABI/version decisions |
| 4 | 16KB page-size check | 04_16kb_check | [x] PASS |
| 5 | Play Console developer account | 05_play_account | [~] created; verification NOT yet submitted (needs ID) |
| 6 | Store listing text + graphics | 06_store_listing | [~] drafted - owner review |
| 7 | Data safety / content rating / declarations | 07_data_safety | [~] drafted; report/block built; DB rules fix pending |
| 8 | Internal -> closed testing -> production | 08_testing_tracks | [ ] |
| 9 | Cleanup / loose ends | 09_cleanup | [ ] |

Critical path: 5 (account verification + the closed-test waiting period) - start early.

Secrets: keystore + passwords live in ~/Documents/rampart_secrets/ (outside the repo, backed up).
Build outputs (.aab/.apk) are gitignored here. Never paste passwords into chat or notes.

## Day-of runbook
05_play_account/WHEN_ID_READY.md lists the exact steps for once identity verification is possible.

## Waiting on the owner
- Review store listing text/graphics (06) and legal.html diff (07), then commit.
- Review + commit report/block (09_cleanup/NOTES.md has deploy order!) and decide on DB rules (09_cleanup/DATABASE_RULES_FINDING.md).
- Submit identity verification; recruit ~15-20 closed testers (08 tracker).
