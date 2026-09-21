# 16KB page-size compliance (Chaquopy/numpy native libs)

Status: NOT STARTED

Play requires 16KB alignment for new apps targeting Android 15+.
targetSdk is 36; Chaquopy plugin 17.0.0; numpy is bundled for the on-device AI.

Steps
- [ ] Extract the arm64-v8a .so files from the release .aab/apk
- [ ] Check ELF LOAD segment alignment >= 0x4000 (`readelf -lW`), and
      `zipalign -c -P 16 4 app-release.apk` on a universal APK from the bundle
- [ ] If any lib fails: bump Chaquopy / numpy version, re-test, re-check
- [ ] Optionally confirm on Play Console pre-launch report after first upload

Done when: all arm64-v8a native libs report 16KB-compatible.
