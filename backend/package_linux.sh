#!/usr/bin/env bash
# Package the frozen PharmMS Linux binary into distributable formats.
#
#   ./package_linux.sh            build AppImage (and .deb if dpkg-deb exists)
#   ./package_linux.sh --appimage-only
#
# WHAT IT PRODUCES
# ----------------
#   dist/PharmMS-x86_64.AppImage   one file, runs on any distro, needs FUSE
#   dist/pharms_1.0.0_amd64.deb    installs on Debian/Ubuntu/Mint
#
# WHY BOTH FORMATS
# An AppImage is the closest thing to the Windows single-.exe story: download,
# chmod +x, run. But AppImage needs FUSE, which Ubuntu 22.04+ ships without by
# default, and a pharmacy machine is exactly the kind of machine nobody wants
# to debug FUSE on. A .deb installs through the package manager with
# dependencies resolved, which is the format a Linux pharmacy user can
# actually be walked through over the phone. Shipping both means the user
# picks whichever their distro handles, and neither blocks the other.

set -euo pipefail
BackendDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ProjectDir="$(dirname "$BackendDir")"
DistDir="$BackendDir/dist"
Binary="$DistDir/PharmMS"
AppName='PharmMS'
Version='1.0.0'
Maintainer='PharmMS'

# --- The icon ---------------------------------------------------------------
# The desktop entry and both package formats reference a PNG; Linux desktop
# environments do not read .ico. The repo ships only pharms.ico, so the PNG is
# converted from it at package time with whatever tool is available (ImageMagick
# or Pillow). If neither exists, IconSource is left empty and the entry is
# written with a bare stem - the app still runs, the desktop just shows the
# generic application icon rather than blocking the build.
IconStem='pharms'
IconSource=''
IcoPath="$BackendDir/pharms.ico"
if command -v magick >/dev/null 2>&1; then
  IconSource="$DistDir/$IconStem.png"
  magick "$IcoPath" "$IconSource" || IconSource=''
elif command -v convert >/dev/null 2>&1; then
  IconSource="$DistDir/$IconStem.png"
  convert "$IcoPath" "$IconSource" || IconSource=''
else
  # Pillow is already a backend dependency (used for image handling), so a
  # frozen build environment almost certainly has it.
  if python3 -c 'import PIL' >/dev/null 2>&1; then
    IconSource="$DistDir/$IconStem.png"
    python3 -c "import sys; from PIL import Image; Image.open(sys.argv[1]).save(sys.argv[2])" \
      "$IcoPath" "$IconSource" || IconSource=''
  fi
fi
[ -n "$IconSource" ] && [ -f "$IconSource" ] \
  && green "Icon: $IconSource" \
  || green 'No PNG icon could be produced; packages will use the generic icon.'

AppimageOnly=0
for arg in "$@"; do
  case "$arg" in
    --appimage-only) AppimageOnly=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

step()  { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
green() { printf '\033[1;32m%s\033[0m\n' "$1"; }
fail()  { printf '\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

[ -f "$Binary" ] || fail "No frozen binary at $Binary. Run ./build_linux.sh first."

# --- desktop entry + icon ----------------------------------------------------
# Both formats need the same desktop entry, so it is built once into a staging
# area and each packager copies it. The icon is a PNG rather than the Windows
# .ico because the Linux desktop environments that read the entry only
# understand raster or SVG images.
step 'Preparing desktop entry and icon'
# The staging area is built UNCONDITIONALLY, not only for the .deb.
#
# The first version staged the desktop entry inside the `if [ $AppimageOnly -eq 0 ]`
# block, so `--appimage-only` reached the AppImage step with no entry staged and
# died on the `fail` below - the option could never succeed, ever. Both
# packagers consume the same entry, so it is staged once for whichever of them
# runs.
Stage="$DistDir/stage"
rm -rf "$Stage"
mkdir -p "$Stage" "$Stage/applications" "$Stage/pixmaps"
cat > "$Stage/applications/pharms.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$AppName
Comment=Pharmacy management system - offline, local-first
Exec=/usr/local/bin/PharmMS
Icon=$IconStem
Categories=Office;Medical;
StartupWMClass=PharmMS
EOF
if [ -n "$IconSource" ]; then
  cp -f "$IconSource" "$Stage/pixmaps/$IconStem.png"
fi

# --- AppImage ---------------------------------------------------------------
if command -v appimagetool >/dev/null 2>&1; then
  step 'Building the AppImage'
  AppDir="$DistDir/PharmMS.AppDir"
  rm -rf "$AppDir"
  mkdir -p "$AppDir/usr/bin" "$AppDir/usr/share/applications"
  cp -f "$Binary" "$AppDir/usr/bin/PharmMS"
  cp -f "$Stage/applications/pharms.desktop" "$AppDir/" \
    || fail 'Could not stage the desktop entry for the AppImage.'
  [ -n "$IconSource" ] && cp -f "$IconSource" "$AppDir/pharms.png"
  # APPIMAGE_TOOL_FLAGS lets a caller add flags needed for its environment.
  # CI (release.yml) sets --appimage-extract-and-run because GitHub runners
  # have no FUSE; a developer machine leaves it unset and the default applies.
  # shellcheck disable=SC2086
  cd "$DistDir" && appimagetool $APPIMAGE_TOOL_FLAGS \
    "PharmMS.AppDir" "PharmMS-x86_64.AppImage"
  rm -rf "$AppDir"
  green "  AppImage: dist/PharmMS-x86_64.AppImage"
elif [ "$AppimageOnly" -eq 1 ]; then
  fail 'appimagetool not found and --appimage-only was requested.'
else
  echo '    appimagetool not found - skipping AppImage.'
  echo '    Install it from https://appimage-tool.readthedocs.io to produce one.'
fi

# --- .deb -------------------------------------------------------------------
if [ "$AppimageOnly" -eq 0 ]; then
  if command -v dpkg-deb >/dev/null 2>&1; then
    step 'Building the .deb'
    # The .deb tree is laid out inside the same stage, adding what only it needs.
    mkdir -p "$Stage/DEBIAN" "$Stage/usr/local/bin" \
             "$Stage/usr/share/applications" "$Stage/usr/share/pixmaps"
    mv -f "$Stage/applications/pharms.desktop" "$Stage/usr/share/applications/pharms.desktop"
    [ ! -f "$Stage/pixmaps/$IconStem.png" ] || \
      mv -f "$Stage/pixmaps/$IconStem.png" "$Stage/usr/share/pixmaps/$IconStem.png"
    cat > "$Stage/DEBIAN/control" <<EOF
Package: pharms
Version: $Version
Architecture: amd64
Maintainer: $Maintainer
Depends: libwebkit2gtk-4.1-0, fuse2 | fuse3
Section: science
Priority: optional
Description: Pharmacy management system - offline, local-first
 A single-user desktop application for managing prescriptions, patient
 records, medicine stock and inventory in a retail pharmacy. All data is
 stored locally in SQLite with encryption at rest for patient and
 prescription records; nothing is pushed online.
 .
 Installs /usr/local/bin/PharmMS and a desktop entry.
EOF
    cp -f "$Binary" "$Stage/usr/local/bin/PharmMS"
    chmod 755 "$Stage/usr/local/bin/PharmMS" \
              "$Stage/DEBIAN/control"
    dpkg-deb --build --root-owner-group "$Stage" "$DistDir/pharms_${Version}_amd64.deb"
    green "  .deb    : dist/pharms_${Version}_amd64.deb"
  else
    echo '    dpkg-deb not found - skipping the .deb.'
    echo '    Build one on a Debian/Ubuntu machine, or with dpkg installed.'
  fi
fi

rm -rf "$Stage"

printf '\n'
green 'Packaging complete.'
printf '  dist/ contents:\n'
ls -la "$DistDir" | grep -Ev '^total|^d' || true
