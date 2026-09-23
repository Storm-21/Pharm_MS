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
# Native commands are the exception. In PowerShell 7 (the version GitHub
# Actions uses for `shell: pwsh`) a native command that writes to stderr raises
# a terminating NativeCommandError under 'Stop', which aborts a build that was
# otherwise fine - npm deprecation notices and pip's resolver output are enough.
# PowerShell 5.1, which a developer machine uses, is more forgiving, so the
# difference only ever shows up on CI. `Continue` for native commands keeps
# real errors fatal (each caller checks its exit code) without turning ordinary
# progress output into a build failure.
$PSNativeCommandUseErrorActionPreference = $false
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

<#
Run the venv Python and judge it only by its exit code.

Mirrors Invoke-Npm below, and exists for the same reason: pip writes resolver
progress and dependency-conflict notices to stderr, and under
$ErrorActionPreference = 'Stop' PowerShell can escalate that into a terminating
error. The PyInstaller install step was the first casualty of this. Exit code is
the only reliable signal.
#>
function Invoke-VenvPython {
    param([string[]]$Arguments, [switch]$Quiet)
    $pyLog = Join-Path $env:TEMP 'pharms_py.log'
    $proc = Start-Process -FilePath $VenvPython -ArgumentList $Arguments `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $pyLog `
        -RedirectStandardError "$pyLog.err"
    if ($proc.ExitCode -ne 0 -and -not $Quiet) {
        Write-Host '--- python output (last 25 lines) ---' -ForegroundColor Yellow
        Get-Content "$pyLog.err" -ErrorAction SilentlyContinue | Select-Object -Last 25
        Get-Content $pyLog -ErrorAction SilentlyContinue | Select-Object -Last 25
    }
    return $proc.ExitCode
}

<#
Run npm and judge it purely by its exit code.

WHY THIS WRAPPER EXISTS
-----------------------
The script runs with $ErrorActionPreference = 'Stop'. npm writes progress and
deprecation notices to stderr, and PowerShell turns any native command's stderr
output into a NativeCommandError record - which, under 'Stop', terminates the
script. The frontend build was therefore able to abort with a success-looking
message like

    (node:1234) [DEP0176] DeprecationWarning: fs.F_OK is deprecated...

before reaching PyInstaller, leaving no .exe behind and no obvious reason why.
Redirecting stderr into the pipeline and checking $LASTEXITCODE explicitly makes
the exit code the only thing that decides success, which is what the note in
the PyInstaller step below already does and for exactly the same reason.
#>
function Invoke-Npm {
    param([string[]]$Arguments)
    $npmLog = Join-Path $env:TEMP 'pharms_npm.log'
    # Resolve npm.cmd specifically. A bare `npm` resolves to npm.ps1 on Windows,
    # and Start-Process cannot execute a PowerShell script as an application -
    # it fails with "%1 is not a valid Win32 application". The .cmd shim is the
    # real entry point.
    $npmCmd = $null
    foreach ($candidate in @('npm.cmd', 'npm.exe')) {
        $found = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($found) { $npmCmd = $found.Source; break }
    }
    if (-not $npmCmd) {
        foreach ($candidate in @('C:\Program Files\nodejs\npm.cmd')) {
            if (Test-Path $candidate) { $npmCmd = $candidate; break }
        }
    }
    if (-not $npmCmd) { Fail 'npm not found. Install Node.js.' }
    $proc = Start-Process -FilePath $npmCmd -ArgumentList $Arguments `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $npmLog `
        -RedirectStandardError "$npmLog.err"
    if ($proc.ExitCode -ne 0) {
        Write-Host '--- npm output (last 30 lines) ---' -ForegroundColor Yellow
        Get-Content "$npmLog.err" -ErrorAction SilentlyContinue | Select-Object -Last 30
        Get-Content $npmLog -ErrorAction SilentlyContinue | Select-Object -Last 30
        Fail "npm $($Arguments -join ' ') failed (exit $($proc.ExitCode))."
    }
    Get-Content $npmLog -ErrorAction SilentlyContinue | Select-Object -Last 5
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
        try { Invoke-Npm -Arguments @('install') | Out-Null } finally { Pop-Location }
    }

    Push-Location $FrontendDir
    try {
        Invoke-Npm -Arguments @('run', 'build') | Out-Null
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

# Query the module through `importlib.util.find_spec`, NOT by running
# `python -m PyInstaller --version`.
#
# WHY: on a clean machine PyInstaller is absent, so Python writes
# "No module named PyInstaller" to stderr. Under $ErrorActionPreference = 'Stop'
# PowerShell turns a native command's stderr into a terminating
# NativeCommandError, so the script died on the probe line - before reaching the
# install below that existed precisely to handle this case. The `*> $null`
# redirect does not prevent it: the error record is created while the command is
# being set up, not from the stream it writes to.
#
# That made the build fail on any fresh checkout, which is every CI run, while
# passing on every developer machine where the package was already installed.
# find_spec returns None instead of raising or writing to stderr, so there is
# nothing for PowerShell to escalate.
$pyInstallerPresent = Invoke-VenvPython -Arguments @('-c', "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)") -Quiet
if ($pyInstallerPresent -ne 0) {
    Write-Host '    PyInstaller missing - installing it...'
    $code = Invoke-VenvPython -Arguments @('-m', 'pip', 'install', '--upgrade', 'pyinstaller')
    if ($code -ne 0) { Fail 'Could not install PyInstaller.' }
    Write-Host '    PyInstaller installed.'
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
