# Version bump and release .aab

Status: NOT STARTED

Steps
- [ ] versionCode / versionName in android_app/android/app/build.gradle
      (currently 1 / "1.0"; versionCode must increase on every Play upload)
- [ ] Decide: drop x86_64 from abiFilters for release (emulator-only, adds size)
- [ ] `cd android_app/android && ./gradlew bundleRelease`
- [ ] Output: android_app/android/app/build/outputs/bundle/release/app-release.aab
- [ ] Record size + versionCode used below

Log
- (none yet)
