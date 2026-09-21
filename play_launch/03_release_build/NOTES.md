# Version bump and release .aab

Status: IN PROGRESS - first signed .aab built 2026-09-21 (versionCode 1, 51 MB). Version bump/ABI decision open.

Steps
- [ ] versionCode / versionName in android_app/android/app/build.gradle
      (currently 1 / "1.0"; versionCode must increase on every Play upload)
- [ ] Decide: drop x86_64 from abiFilters for release (emulator-only, adds size)
- [x] `cd android_app/android && ./gradlew bundleRelease`
- [ ] Output: android_app/android/app/build/outputs/bundle/release/app-release.aab
- [ ] Record size + versionCode used below

Log
- 2026-09-21: BUILD SUCCESSFUL in 1m04s. app-release.aab 51,475,096 bytes, versionCode 1 / 1.0, includes arm64-v8a + x86_64. Composition: 45 MB assets (Chaquopy stdlib+requirements per ABI, web), 11 MB lib/arm64, 11 MB lib/x86_64.
- Recommendation: drop x86_64 for release (saves roughly 15-20 MB); versionCode 1 is fine for the FIRST upload, bump for every later one.
