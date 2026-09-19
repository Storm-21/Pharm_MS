# PharmMS one-command build.
#
#   .\build_exe.ps1                    build PharmMS.exe
#   .\build_exe.ps1 -SkipFrontend      reuse the existing frontend/build
#   .\build_exe.ps1 -Clean             wipe build artefacts first
#
# Produces: backend\dist\PharmMS.exe
#
# The result is a single self-contained file. On a target machine it needs no
# Python, no Node.js and no internet connection.

[CmdletBinding()]
param(
    [switch]$SkipFrontend,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

$BackendDir  = $PSScriptRoot
$ProjectDir  = Split-Path $BackendDir -Parent
$FrontendDir = Join-Path $ProjectDir 'frontend'
$VenvPython  = Join-Path $BackendDir 'venv\Scripts\python.exe'

function Write-Step($message) {
    Write-Host ''
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Fail($message) {
    Write-Host "ERROR: $message" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VenvPython)) {
    Fail "Python venv not found at $VenvPython. Create it with: python -m venv venv"
}

# --- 1. Frontend -------------------------------------------------------------
if (-not $SkipFrontend) {
    Write-Step 'Building the React frontend'
    if (-not (Test-Path $FrontendDir)) { Fail "Frontend folder not found: $FrontendDir" }

    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) {
        $candidate = 'C:\Program Files\nodejs'
        if (Test-Path $candidate) {
            $env:Path = "$candidate;" + $env:Path
            Write-Host "    Added $candidate to PATH for this session."
        } else {
            Fail 'Node.js not found. Install it, or pass -SkipFrontend to reuse an existing build.'
        }
    }

    if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
        Write-Host '    node_modules missing - running npm install...'
        Push-Location $FrontendDir
        try { & npm install } finally { Pop-Location }
    }

    Push-Location $FrontendDir
    try {
        & npm run build
        if ($LASTEXITCODE -ne 0) { Fail 'npm run build failed.' }
    } finally {
        Pop-Location
    }
    Write-Host '    Frontend built.' -ForegroundColor Green
} else {
    Write-Step 'Skipping frontend build (-SkipFrontend)'
}

$indexHtml = Join-Path $FrontendDir 'build\index.html'
if (-not (Test-Path $indexHtml)) {
    Fail "No frontend build at $indexHtml. Run without -SkipFrontend."
}

# --- 1b. Licence key table --------------------------------------------------
# Any keys issued via issue_key.py are compiled in so the app can verify them
# without carrying the signing secret.
Write-Step 'Checking the issued licence-key table'
$IssuedTable = Join-Path $BackendDir 'issued_keys_build.py'
$Generated   = Join-Path $BackendDir 'app\issued_keys_build.py'
if (Test-Path $IssuedTable) {
    Copy-Item $IssuedTable $Generated -Force
    $keyCount = (Select-String -Path $Generated -Pattern '^\s{4}' -AllMatches | Measure-Object).Count
    Write-Host "    embedded $keyCount issued key(s)"
} else {
    Write-Host '    no issued keys yet - run issue_key.py --export if you have sold any'
}

# --- 2. PyInstaller ----------------------------------------------------------
Write-Step 'Ensuring PyInstaller is available'
& $VenvPython -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host '    Installing PyInstaller...'
    & $VenvPython -m pip install --upgrade pyinstaller
    if ($LASTEXITCODE -ne 0) { Fail 'Could not install PyInstaller.' }
}

# --- 3. Clean ----------------------------------------------------------------
if ($Clean) {
    Write-Step 'Cleaning previous build artefacts'
    foreach ($path in @('build', 'dist')) {
        $full = Join-Path $BackendDir $path
        if (Test-Path $full) {
            Remove-Item $full -Recurse -Force
            Write-Host "    Removed $full"
        }
    }
}

# --- 4. Freeze ---------------------------------------------------------------
Write-Step 'Freezing the application (this takes a few minutes)'
Push-Location $BackendDir
try {
    # PyInstaller logs progress to stderr. With $ErrorActionPreference='Stop'
    # PowerShell would treat that as a terminating error, so run it through
    # Start-Process and judge the outcome purely by the exit code.
    $pyiLog = Join-Path $env:TEMP 'pharms_pyinstaller.log'
    $proc = Start-Process -FilePath $VenvPython `
        -ArgumentList @('-m', 'PyInstaller', '--clean', '--noconfirm', 'pharms.spec') `
        -WorkingDirectory $BackendDir `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $pyiLog `
        -RedirectStandardError ("$pyiLog.err")

    if ($proc.ExitCode -ne 0) {
        Write-Host '--- PyInstaller output (last 40 lines) ---' -ForegroundColor Yellow
        Get-Content "$pyiLog.err" -ErrorAction SilentlyContinue | Select-Object -Last 40
        Fail 'PyInstaller failed.'
    }
} finally {
    Pop-Location
}

$exe = Join-Path $BackendDir 'dist\PharmMS.exe'
if (-not (Test-Path $exe)) { Fail "Expected output missing: $exe" }

# --- 5. Report ---------------------------------------------------------------
$sizeMb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host ''
Write-Host '==============================================================' -ForegroundColor Green
Write-Host '  Build complete' -ForegroundColor Green
Write-Host '==============================================================' -ForegroundColor Green
Write-Host "  Executable : $exe"
Write-Host "  Size       : $sizeMb MB"
Write-Host ''
Write-Host '  Run it by double-clicking, or install it with shortcuts:'
Write-Host '      .\install_app.ps1'
Write-Host ''
Write-Host '  It opens in its own desktop window.'
Write-Host ''
Write-Host '  Your database is stored at:'
Write-Host '      %LOCALAPPDATA%\PharmMS\pharmacy.db'
Write-Host '  It survives moving or replacing the .exe. Backups live in a'
Write-Host '  backups\ folder beside it.'
Write-Host '==============================================================' -ForegroundColor Green
