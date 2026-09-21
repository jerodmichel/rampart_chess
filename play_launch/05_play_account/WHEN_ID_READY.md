# Runbook - when you have your ID (Console UI may differ slightly; follow what it shows)

## A. Right now (10-15 min, you)
1. play.google.com/console -> finish "Verify your identity" (government ID + selfie/address as asked).
   Use the same legal name as the payments profile. Submit, then note the date in NOTES.md.
2. Watch the account email (incl. spam) + the Console home page for the result.
3. While waiting you can already: Create app -> name "Rampart Chess", English (US), App, Free,
   accept declarations. Choose to use Play App Signing (default).

## B. Before the first upload (me, no waiting on Google)
- [ ] Owner commits/pushes web/legal.html fixes (review the diff first) -> live at rampartchess.com/legal
- [ ] Owner decides: report/block feature now or after first review (09_cleanup/REPORT_BLOCK_PLAN.md)
- [ ] Re-run android_app/sync-web.py + `npx cap sync android` (legal.html + any web change ships in the app)
- [ ] Bump versionCode (2 if anything above changed and you already uploaded 1; else 1 is fine)
- [ ] `cd android_app/android && ./gradlew bundleRelease` -> app-release.aab (signed with the upload key)
- [ ] Create a THROWAWAY demo account on rampartchess.com (real email you control) for Google reviewers

## C. Console - fill in (all material is in play_launch/)
1. Main store listing: paste text/*.txt, upload assets/icon_512.png, feature_graphic_1024x500.png,
   phone_screenshot_*.png (see 06_store_listing/text/listing_meta.md)
2. App content: Privacy policy URL, Ads = No, App access (give the demo account), Content rating
   questionnaire, Target audience 13+, Data safety (07_data_safety/DRAFT_ANSWERS.md), Account deletion
   URL (rampartchess.com/delete-account), Government/news/health = No.
3. Testing > Internal testing > Create release > upload the .aab > add tester emails > roll out.
   (Internal testers can install within minutes - do this first to smoke-test the real Play build.)
4. Testing > Closed testing (personal account => needed for production): create track, upload the same
   or newer .aab, add a tester list/Google Group of >= ~12 people, send them the opt-in link.
   Keep them opted in ~14 days continuously, then Dashboard > "Apply for production".
5. Pre-launch report: check for crashes and the 16KB warning after the first upload.

## D. After approval
- Production release, staged rollout (e.g. 20% -> 100%). Update memory/notes. Fly: keep ONE machine.
