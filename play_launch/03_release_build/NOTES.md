# Version bump and release .aab

Status: READY TO UPLOAD (pending Play account) - signed .aab rebuilt 2026-09-21 evening with report/block, authz fix, policy text (versionCode 1, 51.5 MB). ABI decision made: KEEP x86_64 in release.

Steps
- [ ] versionCode / versionName in android_app/android/app/build.gradle
      (currently 1 / "1.0"; versionCode must increase on every Play upload)
- [x] DECIDED 2026-09-21: keep arm64-v8a + x86_64 in release. Phones never download x86_64 (Play splits the AAB by ABI); it only enlarges the upload; keeping it allows emulator testing of the exact release build and x86 Chromebooks. (Earlier note claiming it 'saves 15-20 MB' referred to upload size only.)
- [x] `cd android_app/android && ./gradlew bundleRelease`
- [ ] Output: android_app/android/app/build/outputs/bundle/release/app-release.aab
- [ ] Record size + versionCode used below

Log
- 2026-09-21: BUILD SUCCESSFUL in 1m04s. app-release.aab 51,475,096 bytes, versionCode 1 / 1.0, includes arm64-v8a + x86_64. Composition: 45 MB assets (Chaquopy stdlib+requirements per ABI, web), 11 MB lib/arm64, 11 MB lib/x86_64.
- Recommendation: drop x86_64 for release (saves roughly 15-20 MB); versionCode 1 is fine for the FIRST upload, bump for every later one.
- 2026-09-21 (night): server + web deployed by owner (live API has /blocks + /report; live legal/delete-account/main.js verified). Android www re-synced, `bundleRelease` OK, signed (same upload-cert SHA256 as before), contains moderation-ui.js and the fixed main.js. android_app/www changes are UNCOMMITTED.
- versionCode is still 1: fine for the FIRST upload; every later upload (incl. re-uploads to the internal track while smoke-testing) needs a higher number - bump in android_app/android/app/build.gradle before each new bundle.
