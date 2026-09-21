# Release signing key + gradle signing config

Status: DONE - signed release .aab builds and verifies; key + passwords backed up off-machine by user (2026-09-21).

Rules
- The keystore and its passwords live OUTSIDE the repo: ~/Documents/rampart_secrets/
- Back it up to at least one more place (USB / password manager). Losing the
  upload key means a reset request to Google; losing it with no Play App
  Signing means the app can never be updated.
- Enroll in Play App Signing when creating the app in Play Console (Google
  holds the app-signing key; we only hold an upload key).

Steps
- [x] User runs (done 2026-09-20) (own terminal, needs passwords):
      mkdir -p ~/Documents/rampart_secrets && keytool -genkeypair -v \
        -keystore ~/Documents/rampart_secrets/rampart-upload.jks -alias rampart-upload \
        -keyalg RSA -keysize 2048 -validity 10000
- [x] Write ~/Documents/rampart_secrets/keystore.properties (storeFile/storePassword/keyAlias/keyPassword)
- [x] Claude wires (done 2026-09-21, uncommitted) android/app/build.gradle signingConfigs.release to read that
      file (path outside repo; build still works unsigned if the file is absent)
- [ ] Back up the keystore + passwords (record WHERE here, not the secrets):
      backup location: ______________________

Done when: `./gradlew bundleRelease` produces a SIGNED .aab.

Log
- 2026-09-20: rampart-upload.jks created in ~/Documents/rampart_secrets/ (chmod 600 recommended).
- 2026-09-21: build.gradle reads ~/Documents/rampart_secrets/keystore.properties; absent file = unsigned release, debug unaffected. `./gradlew help` parses OK. Still TODO: create keystore.properties, backup, then try a signed bundleRelease (box 3).
- 2026-09-21: first signed bundleRelease OK, jarsigner verifies. Upload cert SHA256 9E:1C:01:24:E2:A1:EC:D8:02:36:F7:B9:00:47:A7:B3:FC:E7:F0:AE:E4:C7:CE:08:6B:64:E0:14:50:76:78:62 (public fingerprint; Play will ask for/show it). Cert subject has country 'C=01' (typo, harmless for an upload key).
- 2026-09-21: user confirmed ~/Documents/rampart_secrets backed up off this machine.
