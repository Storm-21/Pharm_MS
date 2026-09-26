#!/usr/bin/env bash
# PharmMS one-command build for Linux.
#
#   ./build_linux.sh                build the Linux executable
#   ./build_linux.sh --skip-frontend   reuse the existing frontend/build
#   ./build_linux.sh --clean           wipe build artefacts first
#
# Produces: backend/dist/PharmMS
#
# The result is a single self-contained file. On a target machine it needs no
# Python, no Node.js and no internet connection.
#
# WHAT IT NEEDS ON THE BUILD MACHINE
# ----------------------------------
#   python3, python3-venv        the interpreter and the ability to build a venv
#   node + npm                   for the React frontend
#   libwebkit2gtk (GTK backend)  the native window, via pywebview. On Debian/
#                                Ubuntu: sudo apt install libwebkit2gtk-4.1-dev
#                                On Fedora: webkit2gtk4.1-devel
#   python3-dev / gcc            only if a wheel must be compiled (some distros)
#
# WHY PYWEBVIEW NEEDS THE SYSTEM LIBRARY
# The Windows build bundles WebView2 via pywebview's .NET bindings. On Linux
# the window is drawn by webkit2gtk, which is a SYSTEM library - it cannot be
# bundled, because it depends on the desktop's own GTK and glib versions. So
# the Linux payload is "self-contained application, system web renderer", and
# a machine without webkit2gtk falls back to the browser, which desktop_app.py
# does automatically. That fallback is why the script warns rather than fails
# when the library is missing at runtime.

set -euo pipefail
BackendDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ProjectDir="$(dirname "$BackendDir")"
FrontendDir="$ProjectDir/frontend"
VenvPython="$BackendDir/venv/bin/python"

SkipFrontend=0
Clean=0
for arg in "$@"; do
  case "$arg" in
    --skip-frontend) SkipFrontend=1 ;;
    --clean) Clean=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

step()  { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
green() { printf '\033[1;32m%s\033[0m\n' "$1"; }
fail()  { printf '\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

# --- venv --------------------------------------------------------------------
step 'Preparing the Python virtual environment'
if [ ! -x "$VenvPython" ]; then
  echo "    No venv at $BackendDir/venv - creating one..."
  python3 -m venv "$BackendDir/venv" || fail 'python3 -m venv failed. Is python3-venv installed?'
fi
"$VenvPython" -m pip install --upgrade pip --quiet || fail 'pip upgrade failed'
"$VenvPython" -m pip install -r "$BackendDir/requirements.txt" --quiet \
  || fail 'Could not install requirements.txt into the venv.'

# --- 1. Frontend -------------------------------------------------------------
if [ "$SkipFrontend" -eq 0 ]; then
  step 'Building the React frontend'
  command -v node >/dev/null || fail 'Node.js not found. Install it, or pass --skip-frontend to reuse an existing build.'
  if [ ! -d "$FrontendDir/node_modules" ]; then
    echo '    node_modules missing - running npm install...'
    (cd "$FrontendDir" && npm install --no-audit --no-fund) || fail 'npm install failed'
  fi
  (cd "$FrontendDir" && npm run build) || fail 'npm run build failed'
  echo '    Frontend built.'
else
  step 'Skipping frontend build (--skip-frontend)'
fi
[ -f "$FrontendDir/build/index.html" ] || fail "No frontend build at $FrontendDir/build/index.html. Run without --skip-frontend."

# --- 1b. Licence key table ---------------------------------------------------
# Same as the Windows build: keys issued via issue_key.py are compiled in so
# the app can verify them without carrying the signing secret.
step 'Checking the issued licence-key table'
IssuedTable="$BackendDir/issued_keys_build.py"
Generated="$BackendDir/app/issued_keys_build.py"
if [ -f "$IssuedTable" ]; then
  cp -f "$IssuedTable" "$Generated"
  echo "    embedded $(grep -cE '^    ' "$Generated" || true) issued key(s)"
else
  echo '    no issued keys yet - run issue_key.py --export if you have sold any'
fi

# --- 2. PyInstaller ----------------------------------------------------------
step 'Ensuring PyInstaller is available'
if ! "$VenvPython" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)" 2>/dev/null; then
  echo '    PyInstaller missing - installing it...'
  "$VenvPython" -m pip install --upgrade pyinstaller --quiet || fail 'Could not install PyInstaller.'
  echo '    PyInstaller installed.'
fi

# --- 3. Clean ----------------------------------------------------------------
if [ "$Clean" -eq 1 ]; then
  step 'Cleaning previous build artefacts'
  for path in build dist; do
    if [ -d "$BackendDir/$path" ]; then rm -rf "$BackendDir/$path"; echo "    Removed $BackendDir/$path"; fi
  done
fi

# --- 4. Freeze ---------------------------------------------------------------
step 'Freezing the application (this takes a few minutes)'
(cd "$BackendDir" && "$VenvPython" -m PyInstaller --clean --noconfirm pharms.spec) \
  || { echo '--- PyInstaller failed - last 40 lines were printed above ---' >&2; fail 'PyInstaller failed.'; }

Binary="$BackendDir/dist/PharmMS"
[ -f "$Binary" ] || fail "Expected output missing: $Binary"

# --- 5. Report ---------------------------------------------------------------
SizeMb="$(du -m "$Binary" | cut -f1)"
printf '\n'
green '=============================================================='
green '  Build complete'
green '=============================================================='
printf '  Executable : %s\n' "$Binary"
printf '  Size       : %s MB\n' "$SizeMb"
printf '\n'
printf '  Run it:  chmod +x PharmMS && ./PharmMS\n'
printf '  It opens in its own desktop window (WebKit2GTK), or falls\n'
printf '  back to your default browser if the window library is absent.\n'
printf '\n'
printf '  Your database is stored at:\n'
printf '      ~/.local/share/PharmMS/pharmacy.db\n'
printf '  It survives moving or replacing the executable. Backups live\n'
printf '  in a backups/ folder beside it.\n'
green '=============================================================='
