# Porting the original Windows Plants vs. Zombies (1.0.0.1051 and fan mods built on that exe) to native macOS

This guide is the method behind this repository. It covers the global steps, the data-compatibility problems of old or
translated builds, the macOS problems that appear in every port (with their fixes in `patches/pvz-portable-macos.patch`),
and a deliberately light acceptance process. Paths such as `src/...` refer to the patched PvZ-Portable checkout
(`PvZ-Portable/src/...` after `scripts/get_engine.sh`).

## 1. Ground rules

- Never execute a Windows `.exe` or `.dll`. Analyse them statically (`tools/pvzdis.py`, `pediff.py`).
- Keep the user's game folder read-only. Put everything generated in the build folder or a temporary folder.
- Never ship or distribute game assets. Build from the user's own files for personal use only.
- Treat "identical to the Windows version" as the default for gameplay, layout and framing.
- When a mod already implements something itself (its own sun display, HD art, window or resolution handling, fonts),
  keep the mod's logic. Only make it work correctly on macOS (section 6).
- Ask the user before any download, such as an AI upscaler. Ask once about visible product choices, such as a font face or
  framing. Do not re-open a choice the user has already made.
- Run tests in a window only: a background app that never takes focus or the screen. Always pass an absolute scratch
  `-savedir`; never touch the user's saves in `~/Library/Application Support/io.github.wszqkzqk/`.

## 2. Global method (in order)

1. **Identify the base and the delta.**
   - Read the exe version resource. 1.0.0.1051 is the original; 1.2.0.x is GOTY.
   - List the data: `main.pak` (XOR 0xF7 pak, use `tools/pak_tool.py`), loose files that override the pak, and
     `properties/LawnStrings.txt` with its encoding (GBK for Chinese translations).
   - Note fonts, helper DLLs (the 1051 Chinese translation draws text through `gdi42.dll`) and the compiled definition
     format.
   - For a mod, diff its exe against the base exe (`pediff.py`). Cluster the patched bytes, decode each cluster with
     `pvzdis.py`, and write a spec, as in separate analysis notes. Classify each change as gameplay, data, UI/strings
     or engine.
2. **Map the mod onto the engine.**
   - Add a compile flag per edition, like `PVZ_LEGACY_1051` and `PVZ_95` (the latter implies the legacy mode).
   - Put every mod change in `#ifdef` blocks or `PVZ95_VAL(old, new)` style macros, so that the base edition stays
     byte-for-byte identical in behaviour.
3. **Data compatibility.** See section 3. This is usually the largest one-off cost for old or translated builds.
4. **macOS platform layer.** See section 4. This part is the same for every build; reuse the fork's code.
5. **Package.** `zsh scripts/build_apps.sh [--install]`:
   - Build the editions (Release, `PVZ_DEBUG=OFF`).
   - Assemble the resources: reproduce the effective Windows file set, then copy `overrides/` on top.
   - Convert `LawnStrings.txt` to UTF-8.
   - Bundle the dylibs with dylibbundler, sign ad hoc, and write Info.plist with `NSHighResolutionCapable`, a bundle id
     per edition and an AppIcon.
   - Update `dist/` and `/Applications` in place with `rsync`, then run `lsregister -f` for Launchpad.
6. **Verify lightly** (section 5), update `PROJECT_CONTEXT.md` and the changelog, clean up, and report.

## 3. Data-compatibility issues to expect with old or translated builds

| Symptom | Cause | Fix used here |
|---|---|---|
| Reanims, particles or trails fail to load | 1051 ships 32-bit `compiled/*.compiled` definitions only | Legacy compiled loader in `PvzpLib/Definition.cpp` |
| Crashes or blank screens for achievements, Zombatar or quick play | GOTY-only resources are missing | Blank placeholders; disable those screens and widgets in legacy mode |
| English art shows instead of Chinese | The translation renamed the English originals inside the pak (`images`→`jmages` and so on) so that loose Chinese files win | The packaging step reproduces exactly that file set |
| Chinese text missing or shown as boxes | Windows drew every ImageFont string through GDI (`gdi42.dll` TextOutA) with a TTF; the bitmap fonts only carry metrics | `CjkFallbackFont` (stb_truetype, the game's own `fzse_gbk.ttf`) plus emulation of the gdi42 style table (`LegacyGdiStyleOf` in `graphics/ImageFont.cpp`): pixel size, offsets, shadow, inset tint and outline per font |
| Wrapping or centring off; labels overflow buttons | Windows measures CJK as GBK byte widths (2 half-cells) | Keep the byte-width metrics for layout and wrapping (`LegacyGbkByteCount`); never lay out with TTF advances |
| Latin letters in one font are all the same glyph | The translated BrianneTod12 atlas maps every character to one dummy cell | Route that font's ASCII to the TTF as well |
| A stray `]` before the first string (e.g. "]豌豆射手") | `LawnStrings.txt` starts with a space; the parser advanced from the line start, not from the `]` | `PvzpStringListReadName` advances from the name's end (`PvzpLib/PvzpStringFile.cpp`) |
| Player names accept characters Windows rejects | The exe's `AllowChar` permits ASCII letters, digits and space only | Port the filter in legacy builds |

Fidelity rule for text: keep the font the translation ships (方正少儿 is preferred over macOS look-alikes of
YaHei/SimSun). Emulate placement and effects, not faces.

## 4. macOS problems that will appear again, and their fixes

### 4.1 Everything looks blurry on Retina (HiDPI)
- **Cause.** The window was created without `SDL_WINDOW_ALLOW_HIGHDPI`, so the GL drawable is in points and macOS
  upscales the whole frame 2x. Text is rasterised at 800x600 logical size and then magnified as well.
- **Fix** (`platform/default/Window.cpp`, `graphics/GLInterface.*`, `platform/default/Input.cpp`):
  - Request `SDL_WINDOW_ALLOW_HIGHDPI` on macOS. `PVZP_HIDPI=0` restores the old path for A/B tests.
  - `GLInterface::UpdateViewport` letterboxes an exact 4:3 viewport in drawable pixels (sizes rounded to multiples of
    4/3, so a single scale applies to both axes) and stores `mPresentationScale`.
  - Mouse mapping needs a separate window-space rect in points (`mWindowPresentationRect`) for every
    `WidgetManager::Resize` call. Without it, clicks miss by a factor of 2.
  - Recompute on `SIZE_CHANGED`, `RESIZED` and `DISPLAY_CHANGED`, and whenever the drawable or window size changes without
    an event (a pixel-density change when moving to another display).
  - Re-apply `glViewport` before every batch: AppKit resets it when the window moves, which stretches the frame and
    breaks clicks.
  - Rasterise TrueType glyphs at drawable resolution (`CjkFallbackFont::GetScaledGlyph`). Keep every advance, wrap and
    offset at the logical size, place the bitmap at the logical origin plus physical offset / scale, and pixel-snap it.
    Bound the cache: flush it when the scale changes.
  - `glPixelStorei(GL_UNPACK_ALIGNMENT, 1)`. Single NPOT textures with odd-width 16-bit formats otherwise shear and read
    garbage (a coloured line in a dialog, diagonally sheared icons).
  - Acceptance check: at scale 1.0 the output must be pixel-identical to the old build.

### 4.2 Sharpening filter for magnified art (and its performance)
- Bilinear magnification of 800x600-era art at 2-3.7x looks soft.
- **Fix** (`GLInterface.cpp`, `SampleCubic`; `PVZP_FILTER=catmullrom|mitchell|bilinear`):
  - Catmull-Rom in the fragment shader, only when the presentation scale is > 1.
  - Use the 5-tap bilinear-optimised form.
  - Upload alpha textures premultiplied so the negative lobes cannot create halos, and clamp to `u_uvBounds` so atlas
    cells do not bleed.
  - Use separate basic and filtered shader programs.
  - Nearest-filtered draws at non-integer scales use sharp-bilinear.
- **Performance trap.**
  - A 16-tap straight-alpha version made heavy scenes GPU-bound: 30-45 fps, frames alternating 16.7 and 33 ms, which users
    see as periodic stutter.
  - Keep the 5-tap version and a per-frame "cubic budget": past ~26 Mpx of cubic area, sprites fall back to bilinear and
    backgrounds and UI stay cubic.
  - Check the GPU load of light scenes (menus) too.

### 4.3 Sun counter (or any numeric HUD label)
- **Problems.**
  - A mod can raise the sun cap (95: 9990 → 2,000,000,000), so the label overflows its paper.
  - Bitmap digits also sit ~5 px high, because Windows drew this font through GDI with a +4 px style offset.
- **Fix** (`Lawn/SeedPacket.cpp`, `DrawSunMoneyLabel`):
  - Measure the paper's white area from `SeedBank.png`.
  - Centre the label's real ink box, computed from the glyph data, on it.
  - If the ink is wider than the paper (46 px), scale it down uniformly about the centre with
    `PvzpDrawStringMatrix`.
  - Up to 4 digits are drawn unscaled on whole pixels.
- If a mod has its own counter logic, keep it and only check centring and fit at Retina scales.

### 4.4 Blurry small artwork (challenge, puzzle and survival covers)
- **Problem.** `Challenge_Thumbnails.jpg` / `Survival_Thumbnails.jpg` are tiny compressed JPEGs (80x65 cells) and stay
  blurry even with a good filter.
- **Fix.**
  - Upscale them offline with an AI upscaler (needs user approval to download). Here: waifu2x-ncnn-vulkan, models-cunet,
    2x with noise 1 plus TTA, then 2x with noise -1 plus TTA.
  - Pad each cell with 8 px of edge replication before upscaling and crop it afterwards, so neighbouring cells never mix.
  - Real-CUGAN was sharper but invented content and was rejected.
  - Ship 2x, 3x and 4x sheets in `overrides/images/`.
  - `ChallengeScreen.cpp` (`HdThumbnailScaleFor`) picks the sheet that matches the presentation scale and falls back to
    the original when a file is missing. Cache the sheet: decoding the 4x PNG on every screen open costs 30-80 ms.
  - Record provenance: `tools/thumbs/README.md` (tool, version, model, settings, hashes, regenerate script).
- Mods that ship their own HD art need none of this; only check that minification looks clean.

### 4.5 Window and fullscreen behaviour
- **Fullscreen.**
  - Use `SDL_WINDOW_FULLSCREEN_DESKTOP`.
  - The green button and Ctrl+Cmd+F only produce `SIZE_CHANGED`, so resync `mIsWindowed` (the Options checkbox and the
    saved mode) on every fullscreen-flag change.
  - On leaving fullscreen, restore a centred 800x600-point window; otherwise the window is screen-sized and the picture
    is drawn at the wrong scale.
- **Framing.** Keep the original 4:3 in both modes. Fullscreen = 4:3 at full screen height with plain black side bars.
  - Do not build widescreen extensions. Extending the lawn to the right reveals zombies popping into existence (they spawn
    just past the original right edge), and the menu, almanac and store art is 4:3 only.
  - Blurred or mirrored fills were tried and rejected.
- **Windowed 4:3 lock** (`platform/default/MacWindowAspect.mm`, Apple-only Objective-C++):
  - Set `NSWindow.contentAspectRatio`, and wrap SDL's delegate `windowWillResize:toSize:` (`PvzpWindowWillResize`) to round
    to 4k x 3k points, so live drags scale proportionally and the drawable never has even 1 px of bar.
  - Handle the zoom standard frame (largest 4:3).
  - After tiling or programmatic resizes, snap back to 4:3 once the size has been stable for 150 ms.
  - Lock off in fullscreen.
  - `SDL_SetWindowSize` is ignored while the window is zoomed, so the snap uses `setFrame:display:`.
- **Defaults.** The first launch is fullscreen when the build's partner.xml says so (as on Windows); the last mode is
  remembered.

### 4.6 Stutter and frame pacing
Diagnose with the hitch logger before changing anything: `hitchlog MS` in the test hook (`misc/PvzpHitch.h`) logs
every long frame with its time split and what happened inside it.
- **Mid-level first-use loads (30-117 ms).** 1051-style data ships loose compiled definitions that the stock preload
  lists miss; resumed levels skip the intro preload entirely.
  - Call `ReanimatorPreloadAllDefinitions()` in `LawnApp::LoadingThreadProc` (about 1 s more on the loading bar).
- **Catch-up bursts.** After any stall the 100 Hz logic ran up to 9 steps in one frame, which is a second hitch.
  - Lower the backlog limit so recovery takes one small step.
- **Audio-lock waits.** The music update makes several `Mix_*` calls per tick, each taking the audio lock.
  - Skip the redundant ones.
- **Vsync.** Use adaptive vsync on macOS (`SDL_GL_SetSwapInterval(-1)`, falling back to 1).
- **Remaining long frames** are usually window-server or driver waits on a loaded machine. Judge them on a quiet machine.
- **Not hitches.** Test screenshots at full drawable resolution stall the game for 0.4-2 s. Never judge smoothness or
  animation timing from shot bursts; use `fps` and `hitchlog` without shots.

### 4.7 Smaller macOS details
- **Saves.** Use a per-edition save folder (`PvZ1051-Mac`, `PvZ95-Mac`) so editions never share saves.
  `SDL_GetPrefPath` creates the default folder even when `-savedir` is given; that is harmless.
- **iCloud Desktop.** Deleting and recreating folders creates "name 2" conflict copies. Update `build/res`, `dist` and
  `/Applications` in place.
- **Launchpad.** Run `lsregister -f` after installing, then check the Launchpad database for both bundle ids.
- **Icons.** Make an AppIcon.icns per edition, with a badge for the mod.

## 5. Light review and acceptance

Keep it short. One implementer, one quick acceptance pass, and at most one fix round. Full multi-agent verification only
for large engine changes (a new rendering path or a new edition).

**Tools.**
- Test hook: env `PVZP_TEST_SCRIPT` and `PVZP_TEST_SHOTDIR`; commands are listed at the top of
  `misc/PvzpTestHook.cpp` (`shot`, `shotlogical`, `shotfull`, `wclick`, `winsize`, `logstate`, `fps`, `hitchlog`,
  `waitsound`, and others).
- Test mode starts a windowed 800x600 background app. `PVZP_TEST_NO_ASPECT_LOCK=1` lets a test window keep a 16:10 size,
  which shows the same pillarboxed picture as fullscreen.
- Runner: `tools/runtest.sh`.
- Cheats need a `-DPVZ_DEBUG=ON` build plus `-cheat` (`u` unlocks everything on the main menu).
- Keep a copy of the previous installed apps as the baseline.

**Acceptance checklist** (both editions, about 15 minutes):
1. All build trees compile with 0 errors and no new warnings.
2. One smoke script, windowed 800x600 and 1000x750 points:
   - main menu shot;
   - options;
   - almanac plant page (title text);
   - challenge page (covers);
   - a lawn level for about 1 minute: plant and collect sun with `wclick`; the sun counter is centred; `fps` reads about
     60.
3. A 1280x800 window with `PVZP_TEST_NO_ASPECT_LOCK=1`: original framing with pure black bars.
4. Only what the change touched, compared against the baseline with `shotlogical` crops.

**Release.**
- Run `zsh scripts/build_apps.sh --install`.
- Launch each installed app through LaunchServices (`open -n -g -W --env ... --args -savedir=<scratch>`), check
  `codesign --verify --deep`, then check Launchpad.
- Update `PROJECT_CONTEXT.md` and the changelog (the shared root uses the lock), move superseded files to the Trash, and
  report in Chinese.

**Do not.**
- Run real fullscreen in tests.
- Run tests with the default save folder.
- Run long multi-round verification for small UI tweaks.
- Run several agents that edit the same source files at the same time without a file-ownership split.

## 6. Porting another mod with this playbook

1. Diff the mod against the base it was built from (section 2, step 1) and write the spec.
2. Reuse this fork. Add a compile flag for the mod and port its gameplay, data and string changes inside `#ifdef`s.
3. For each item in section 4, decide whether the mod already handles it:

| If the mod already has... | Do |
|---|---|
| Its own sun or HUD logic | Keep it; check centring and fit at Retina scales |
| HD or redrawn art | Keep it; skip 4.4; check that minification is clean and that the filter budget still holds 60 fps |
| Its own resolution, widescreen or window logic | Keep its framing; make sure the HiDPI viewport, the window-space mouse rect and the 4:3 lock (or the mod's own ratio) agree, and that fullscreen toggles resync |
| Its own font rendering | Keep it; check it at drawable resolution |
| Nothing special | Apply section 4 as is |

4. Always keep the fixes that apply to every build: HiDPI (4.1), the filter and its budget (4.2), the fullscreen resync
   and window behaviour (4.5), smoothness (4.6) and packaging details (4.7).
5. Run the acceptance in section 5, package, install, record and report.
