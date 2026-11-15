#!/bin/zsh
# Build the two native macOS apps (original 1.0.0.1051 Chinese edition and the 95 edition)
# from the patched PvZ-Portable checkout (default ./PvZ-Portable, see scripts/get_engine.sh) and YOUR OWN copy of the
# Windows game data (default ./game; it must contain main.pak, properties/LawnStrings.txt, fzse_gbk.ttf and the
# translation's loose folders). No game data is part of this repository.
#
# usage: zsh scripts/build_apps.sh [--install]
#   PVZ_SRC=<dir>       engine checkout (default <repo>/PvZ-Portable)
#   PVZ_GAME_DIR=<dir>  game data folder (default <repo>/game)
#   --install   also copy both apps into /Applications (replacing earlier copies)
set -euo pipefail

ROOT="${0:A:h:h}"                       # repository root
SRC="${PVZ_SRC:-$ROOT/PvZ-Portable}"
DATA="${PVZ_GAME_DIR:-$ROOT/game}"
BUILD="$ROOT/build"
DIST="$ROOT/dist"
PKG="$ROOT"                             # optional overrides/ and icons/ folders
INSTALL=0
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
[[ "${1:-}" == "--install" ]] && INSTALL=1

EDITIONS=(${=EDITIONS:-orig p95})   # override with EDITIONS=orig to build one edition

echo "==> Building engines: ${EDITIONS[*]}"
if (( ${EDITIONS[(Ie)orig]} )); then
  cmake -G Ninja -S "$SRC" -B "$BUILD/orig" -DCMAKE_BUILD_TYPE=Release -DPVZ_95=OFF -DPVZ_LEGACY_1051=ON -DPVZ_DEBUG=OFF >/dev/null
  cmake --build "$BUILD/orig"
fi
if (( ${EDITIONS[(Ie)p95]} )); then
  cmake -G Ninja -S "$SRC" -B "$BUILD/p95" -DCMAKE_BUILD_TYPE=Release -DPVZ_95=ON -DPVZ_DEBUG=OFF >/dev/null
  cmake --build "$BUILD/p95"
fi

echo "==> Assembling game resources"
# The Chinese translation renamed the English originals inside main.pak (images->jmages, data->eata,
# particles->qarticles, properties->qroperties, reanim->seanim) so that its loose files win.
# Reproduce the effective file set: real-named pak folders + loose overrides.
# On an iCloud-synced Desktop, deleting and recreating folders quickly makes iCloud leave "name 2" conflict
# copies, so stage outside the repository (temp dir) and update build/res and dist in place.
TMPWORK="$(mktemp -d "${TMPDIR:-/tmp}/pvzres.XXXXXX")"
STAGE="$TMPWORK/stage"
NEWRES="$TMPWORK/res"
RES="$BUILD/res"
python3 -I "$ROOT/tools/pak_tool.py" extract "$DATA/main.pak" "$STAGE" >/dev/null
mkdir -p "$NEWRES"
for d in compiled data images particles properties reanim sounds; do
  [[ -d "$STAGE/$d" ]] && cp -R "$STAGE/$d" "$NEWRES/"
done
for d in data images particles properties reanim; do
  [[ -d "$DATA/$d" ]] && cp -R "$DATA/$d/." "$NEWRES/$d/"
done
iconv -f GB18030 -t UTF-8 "$DATA/properties/LawnStrings.txt" > "$NEWRES/properties/LawnStrings.txt"
rm -f "$NEWRES/properties/partner.xml.sig"
cp "$DATA/fzse_gbk.ttf" "$NEWRES/"
if [[ -d "$PKG/overrides" ]]; then
  cp -R "$PKG/overrides/." "$NEWRES/"
fi
mkdir -p "$RES"
rsync -a --delete "$NEWRES/" "$RES/"
rm -rf "$TMPWORK"

make_app() {
  local NAME="$1" FLAVOR="$2" BUNDLE_ID="$3" ICON="$4" VERSION="$5"
  # dylibbundler mishandles spaces in paths, so assemble in a space-free temp dir.
  local WORK="$(mktemp -d "${TMPDIR:-/tmp}/pvzapp.XXXXXX")"
  local APP="$WORK/App.app"
  echo "==> Packaging $NAME.app"
  mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$APP/Contents/Frameworks"
  cp "$BUILD/$FLAVOR/pvz-portable" "$APP/Contents/MacOS/PlantsVsZombies"
  strip -x "$APP/Contents/MacOS/PlantsVsZombies"
  cp -R "$RES/." "$APP/Contents/Resources/"
  # Icons are not shipped (they would be game art); put your own icons/<orig|p95>.icns here if you like.
  [[ -f "$PKG/icons/$ICON.icns" ]] && cp "$PKG/icons/$ICON.icns" "$APP/Contents/Resources/AppIcon.icns"
  cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key><string>zh_CN</string>
  <key>CFBundleExecutable</key><string>PlantsVsZombies</string>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundleName</key><string>$NAME</string>
  <key>CFBundleDisplayName</key><string>$NAME</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.games</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSSupportsAutomaticGraphicsSwitching</key><true/>
  <key>NSHumanReadableCopyright</key><string>Engine: PvZ-Portable (LGPL-3.0-or-later). Game data: user-supplied.</string>
</dict>
</plist>
PLIST
  # Bundle Homebrew dylibs so the app does not depend on /opt/homebrew at run time.
  dylibbundler -of -b -x "$APP/Contents/MacOS/PlantsVsZombies" -d "$APP/Contents/Frameworks" \
    -p @executable_path/../Frameworks/ >/dev/null
  # sdl2-compat loads SDL3 with dlopen(), which dylibbundler cannot see.
  local SDL3="$(brew --prefix sdl3)/lib/libSDL3.0.dylib"
  install -m 755 "$SDL3" "$APP/Contents/Frameworks/libSDL3.0.dylib"
  ln -sf libSDL3.0.dylib "$APP/Contents/Frameworks/libSDL3.dylib"
  install_name_tool -id @rpath/libSDL3.0.dylib "$APP/Contents/Frameworks/libSDL3.0.dylib"
  for f in "$APP/Contents/Frameworks/"*.dylib; do
    [[ -L "$f" ]] || codesign --force -s - "$f" >/dev/null 2>&1
  done
  codesign --force --deep -s - "$APP" >/dev/null 2>&1
  codesign --verify --deep "$APP"
  mkdir -p "$DIST/$NAME.app"
  rsync -a --delete "$APP/" "$DIST/$NAME.app/"
  codesign --verify --deep "$DIST/$NAME.app"
  rm -rf "$WORK"
}

mkdir -p "$DIST"
(( ${EDITIONS[(Ie)orig]} )) && make_app "植物大战僵尸" orig "local.pvzmac.original1051" orig "1.0.0.1051"
(( ${EDITIONS[(Ie)p95]} )) && make_app "植物大战僵尸95版" p95 "local.pvzmac.edition95" p95 "1.0.95"

if (( INSTALL )); then
  for n in "植物大战僵尸" "植物大战僵尸95版"; do
    [[ -d "$DIST/$n.app" ]] || continue
    # Update in place so Launchpad and the Dock keep the app's position, then refresh LaunchServices
    # (name, icon) so Launchpad shows the current bundle.
    mkdir -p "/Applications/$n.app"
    rsync -a --delete "$DIST/$n.app/" "/Applications/$n.app/"
    codesign --verify --deep "/Applications/$n.app"
    touch "/Applications/$n.app"
    "$LSREGISTER" -f "/Applications/$n.app"
    echo "Installed /Applications/$n.app"
  done
fi
echo "Done: $DIST"
