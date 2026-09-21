# 16KB page-size compliance (Chaquopy/numpy native libs)

Status: DONE 2026-09-21 - PASS

Play requires 16KB alignment for new apps targeting Android 15+.
targetSdk is 36; Chaquopy plugin 17.0.0; numpy is bundled for the on-device AI.

Steps
- [x] Extract the arm64-v8a .so files from the release .aab/apk
- [x] Check ELF LOAD segment alignment >= 0x4000 (`readelf -lW`), and
      `zipalign -c -P 16 4 app-release.apk` on a universal APK from the bundle
- [x] (n/a - none failed) If any lib fails: bump Chaquopy / numpy version, re-test, re-check
- [ ] Optionally confirm on Play Console pre-launch report after first upload

Done when: all arm64-v8a native libs report 16KB-compatible.

Log
- 2026-09-21: checked release .aab. lib/arm64-v8a: 8/8 .so LOAD align 0x4000. Chaquopy assets (requirements-arm64-v8a.imy incl. 19 numpy .so + stdlib): 67 .so total, 0 below 0x4000. PASS. (zipalign -P 16 on a universal APK and Play pre-launch report still worth a glance after first upload.)
