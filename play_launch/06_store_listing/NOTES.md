# Store listing text + graphics

Status: DRAFTED 2026-09-21 - text/ and assets/ complete, owner to review; not uploaded.

Put drafts in text/ and image files in assets/ (see subfolders).
- [ ] App name (<=30 chars), short description (<=80), full description (<=4000)
- [ ] App icon 512x512 PNG
- [ ] Feature graphic 1024x500
- [ ] Phone screenshots (min 2, up to 8; landscape is fine for this game)
- [ ] Category (Board / Strategy), contact email (apecrank@gmail.com), website rampartchess.com
- [ ] Privacy policy URL: https://rampartchess.com/legal

## REAL-APP SCREENSHOTS 2026-09-21 (late) - assets/real/
Captured from the real signed release APK running in an Android emulator (AVD `rampart_169`, Pixel 2 = 16:9, so landscape
is exactly 1920x1080; the Pixel 6 AVD is 2.22:1 and would be REJECTED - Play caps the ratio at 2:1). Fullscreen board, vs-AI game
(Cletus, Medium), no OS chrome. Flattened to 24-bit RGB (Play rejects alpha). 0.24 MB each.
- real_1_opening_1920x1080.png   - opening position
- real_2_legal_moves_1920x1080.png - a Raider selected, legal squares dotted
- real_3_midgame_1920x1080.png   - mid-game (AI Knight has crossed the rampart; yellow last-move highlights)
The three owner-reviewed drafts in assets/ are untouched (also 24-bit RGB, also 1920x1080). Use whichever set you prefer; they show
the same UI. Not yet uploaded anywhere. Known cosmetic: the round X (exit fullscreen) button overlaps the "A" of the top-left deck label.
Observed in the emulator (real-phone behavior UNVERIFIED): entering fullscreen while in portrait shows the "Rotate your device to
landscape" overlay - screen.orientation.lock('landscape') (web/js/mobile.js, best-effort by design) was not honored by the
Android WebView. Players with auto-rotate on just turn the phone; players with rotation locked would have to unlock it. A native
landscape lock (small Capacitor/Java change) would make this smoother - optional, not a store blocker.

## Feature graphic UPDATE 2026-09-22
Replaced feature_graphic_1024x500.png: same layout/crown/rule as before, new tagline "Chess and cards,
transmuted. A game of pure strategy." (echoes short_description.txt's "while remaining a game of pure
strategy"), queen art re-cropped centered on the face (was showing the "Rampart" script sliver + dark
spire edge before), fades on all sides. Rebuilt with PIL from web/assets/misc/logo_crown.png +
fonts/cinzel/Cinzel-SemiBold.ttf + rampart_bg.png (no source file existed for the original - recreated
to match). 1024x500, RGB, no alpha - matches Play's requirement.
