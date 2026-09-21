# Release signing key + gradle signing config

Status: NOT STARTED

Rules
- The keystore and its passwords live OUTSIDE the repo: ~/rampart_secrets/
- Back it up to at least one more place (USB / password manager). Losing the
  upload key means a reset request to Google; losing it with no Play App
  Signing means the app can never be updated.
- Enroll in Play App Signing when creating the app in Play Console (Google
  holds the app-signing key; we only hold an upload key).

Steps
- [ ] User runs (own terminal, needs passwords):
      mkdir -p ~/rampart_secrets && keytool -genkeypair -v \
        -keystore ~/rampart_secrets/rampart-upload.jks -alias rampart-upload \
        -keyalg RSA -keysize 2048 -validity 10000
- [ ] Write ~/rampart_secrets/keystore.properties (storeFile/storePassword/keyAlias/keyPassword)
- [ ] Claude wires android/app/build.gradle signingConfigs.release to read that
      file (path outside repo; build still works unsigned if the file is absent)
- [ ] Back up the keystore + passwords (record WHERE here, not the secrets):
      backup location: ______________________

Done when: `./gradlew bundleRelease` produces a SIGNED .aab.
