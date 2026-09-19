# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build specification for PharmMS.

Build with:
    pyinstaller --clean --noconfirm pharms.spec

The React bundle in frontend/build is embedded under frontend_build/ so the
executable is genuinely self-contained - no Node.js, no separate web server and
no network access are required on the target machine.

The SQLite database is NOT embedded. app._resolve_data_dir() places it beside
the executable at runtime so each installation keeps its own data, and so
replacing the .exe never destroys the user's records.
"""

from pathlib import Path

# Paths resolved relative to this spec file (backend/).
BACKEND_DIR = Path(SPECPATH).resolve()
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_BUILD = PROJECT_DIR / 'frontend' / 'build'

if not (FRONTEND_BUILD / 'index.html').exists():
    raise SystemExit(
        f"Frontend build not found at {FRONTEND_BUILD}.\n"
        "Run 'npm run build' in frontend/ first (build_exe.ps1 does this for you)."
    )

datas = [
    (str(FRONTEND_BUILD), 'frontend_build'),
]

# Hidden imports that Flask / SQLAlchemy / pywebview load dynamically and
# PyInstaller cannot discover by static analysis.
hiddenimports = [
    'flask_sqlalchemy',
    'sqlalchemy',
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.sqlite',
    'flask_cors',
    'app.data',
    'app.data.seed_medicines',
    'app.data.seed_medicines_extra',
    'app.data.seeder',
    'app.routes',
    'app.routes.security_routes',
    'app.routes.storage_routes',
    'app.models',
    'app.services',
    'app.services.storage_service',
    'app.branding',
    'app.security',
    # Native window stack
    'webview',
    'webview.platforms.edgechromium',
    'webview.platforms.winforms',
    'clr_loader',
    'pythonnet',
]

a = Analysis(
    ['desktop_app.py'],
    pathex=[str(BACKEND_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Keep the reference-data modules: they are pure data and must not be
    # tree-shaken away.
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PIL', 'pytest'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PharmMS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX-packed binaries are commonly flagged by AV scanners
    upx_exclude=[],
    runtime_tmpdir=None,
    # windowed: the app is a native desktop window, so no console flashes up.
    # Set PHARMS_CONSOLE=1 at build time (or flip this to True) to get a
    # console back for diagnosing a startup problem on a new machine.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BACKEND_DIR / 'pharms.ico') if (BACKEND_DIR / 'pharms.ico').exists() else None,
)
