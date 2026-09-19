# Publish PharmMS to GitHub.
#
#   .\publish_github.ps1 -Repo "yourname/pharms"                first release
#   .\publish_github.ps1 -Repo "yourname/pharms" -Tag v2.0.1    later release
#   .\publish_github.ps1 -Repo "..." -SkipRelease               push code only
#
# What this does:
#   1. Checks git is available and the repository is in a clean, sane state
#   2. Creates .gitignore / .gitattributes if missing (build output and the
#      database are never committed)
#   3. Commits the source and pushes to GitHub
#   4. Builds the installer, then uploads it as a GitHub Release asset so
#      anyone can download one file and run it
#
# REQUIREMENTS
#   * git installed and on PATH
#   * a GitHub personal access token with "repo" scope, exported as:
#         $env:GITHUB_TOKEN = "ghp_..."
#     Create one at https://github.com/settings/tokens
#
# The token is only ever read from the environment. It is never written to
# disk, never echoed, and never included in a commit.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Repo,

    [string]$Tag = 'v2.0.0',
    [string]$ReleaseName = '',

    [switch]$SkipBuild,
    [switch]$SkipRelease,
    [switch]$Private
)

$ErrorActionPreference = 'Stop'

$ProjectDir = Split-Path $PSScriptRoot -Parent
$BackendDir = $PSScriptRoot
$SetupExe   = Join-Path $BackendDir 'dist\PharmMS-Setup.exe'
$AppVersion = '2.0.0'

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }

if (-not $ReleaseName) { $ReleaseName = "PharmMS $Tag" }

# --- Preflight ---------------------------------------------------------------
Write-Step 'Preflight checks'

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Fail "git not found on PATH. Install Git for Windows, or push manually using the URLs printed at the end."
}

$inRepo = (& git -C $ProjectDir rev-parse --is-inside-work-tree 2>&1)
if ($inRepo -notmatch 'true') {
    Write-Host '    No git repository here yet - initialising one.'
    & git -C $ProjectDir init | Out-Null
    & git -C $ProjectDir branch -M main | Out-Null
}

if (-not $SkipRelease) {
    if (-not $env:GITHUB_TOKEN) {
        Fail @"
No GITHUB_TOKEN in the environment, so the release upload cannot run.

Create a token with "repo" scope at https://github.com/settings/tokens
then set it for this session and re-run:

    `$env:GITHUB_TOKEN = "ghp_your_token_here"
    .\publish_github.ps1 -Repo "$Repo"
"@
    }
    Write-Host '    GITHUB_TOKEN present'
}

# --- .gitignore / .gitattributes --------------------------------------------
Write-Step 'Ensuring .gitignore and .gitattributes'

$gitignore = Join-Path $ProjectDir '.gitignore'
if (-not (Test-Path $gitignore)) {
    @'
# --- Python ---
__pycache__/
*.py[cod]
*.egg-info/
.Python
venv/
.venv/
env/
ENV/

# --- Node / React ---
node_modules/
npm-debug.log*
yarn-error.log*
.pnp.*
.eslintcache

# --- Build output (regenerate with build_exe.ps1 / npm run build) ---
backend/build/
backend/dist/
backend/_pyinstaller/
frontend/build/
frontend/public/logo*.png
frontend/public/logo.svg
frontend/public/favicon.ico
backend/pharms.ico

# --- Databases: NEVER commit patient data ---
*.db
*.db-journal
*.db-wal
*.db-shm
pharmacy.db
backups/
exports/

# --- Local secrets and private key tooling ---
.env
.env.*
!.env.example
*.key
*.pem
licence-secret.txt
issuer-secret.txt
# --- Licence key issuance: private to the vendor, never publish ---
# issue_key.py holds the signing workflow; issued_keys.json is the list of
# every key sold, including pharmacy names and payment records.
backend/issue_key.py
backend/issued_keys.json
backend/issued_keys_build.py
backend/app/issued_keys_build.py

# --- Editors / OS ---
.vscode/
.idea/
*.swp
Thumbs.db
Desktop.ini
'@ | Set-Content -Path $gitignore -Encoding UTF8
    Write-Host '    wrote .gitignore'
} else {
    Write-Host '    .gitignore already present'
}

$gitattributes = Join-Path $ProjectDir '.gitattributes'
if (-not (Test-Path $gitattributes)) {
    @'
# Normalise line endings so Windows scripts and cross-platform sources agree.
* text=auto eol=lf
*.ps1 text eol=crlf
*.cmd text eol=crlf
*.bat text eol=crlf

# Binary assets - never diff or merge these.
*.png binary
*.jpg binary
*.ico binary
*.exe binary
*.db binary
'@ | Set-Content -Path $gitattributes -Encoding UTF8
    Write-Host '    wrote .gitattributes'
}

# --- Commit ------------------------------------------------------------------
Write-Step 'Staging and committing'

& git -C $ProjectDir add -A
$staged = & git -C $ProjectDir diff --cached --name-only
if (-not $staged) {
    Write-Host '    nothing to commit'
} else {
    $count = ($staged | Measure-Object).Count
    Write-Host "    $count file(s) staged"
    & git -C $ProjectDir commit -m "PharmMS $AppVersion" | Out-Null
    Write-Host '    committed'
}

# --- Remote ------------------------------------------------------------------
Write-Step 'Configuring the remote'

$remoteUrl = "https://github.com/$Repo.git"
$existing = (& git -C $ProjectDir remote 2>&1)
if ($existing -contains 'origin') {
    & git -C $ProjectDir remote set-url origin $remoteUrl
    Write-Host "    origin -> $remoteUrl"
} else {
    & git -C $ProjectDir remote add origin $remoteUrl
    Write-Host "    origin added -> $remoteUrl"
}

# --- Build the installer -----------------------------------------------------
if (-not $SkipRelease) {
    if (-not $SkipBuild) {
        Write-Step 'Building the installer'
        & (Join-Path $BackendDir 'build_installer.ps1')
        if ($LASTEXITCODE -ne 0) { Fail 'Installer build failed.' }
    }
    if (-not (Test-Path $SetupExe)) {
        Fail "Installer not found at $SetupExe. Run build_installer.ps1 first, or drop -SkipRelease."
    }
}

# --- Push --------------------------------------------------------------------
Write-Step "Pushing to $Repo"

# Push using the token in the URL so no interactive prompt is needed. The token
# is held only in this process's memory.
$pushUrl = "https://$($env:GITHUB_TOKEN)@github.com/$Repo.git" 
if ($SkipRelease) { $pushUrl = $remoteUrl }

try {
    & git -C $ProjectDir push -u $pushUrl main --force-with-lease 2>&1 |
        Where-Object { $_ -notmatch 'ghp_|GITHUB_TOKEN' } |
        ForEach-Object { Write-Host "    $_" }
} catch {
    Write-Host "    push reported: $($_.Exception.Message)" -ForegroundColor Yellow
}

# --- Release -----------------------------------------------------------------
if (-not $SkipRelease) {
    Write-Step "Creating GitHub release $Tag"

    $headers = @{
        Authorization          = "token $($env:GITHUB_TOKEN)"
        Accept                 = 'application/vnd.github+json'
        'X-GitHub-Api-Version' = '2022-11-28'
    }

    # Release body: the download instructions a visitor actually needs.
    $body = @"
## PharmMS $AppVersion - Pharmacy Management System

Designed & Developed by Jayant

### Download and install

1. Download **PharmMS-Setup.exe** below
2. Double-click it
3. Click **Install**

No Python, no Node.js, no administrator rights, and no internet connection are
required. Installs to your user folder and adds Desktop and Start Menu shortcuts.

Your records are stored at `%LOCALAPPDATA%\PharmMS` - outside the program
folder - so upgrading or reinstalling never deletes your data.

### What it does

- Medicine database with molecular formulas, manufacturers, Indian Pharmacopoeia
  and BP/USP monograph references, dosing and risk information
- Patient records with allergy tracking and cross-reactivity screening
- Prescription writer with live safety checks, printed on your own letterhead
- Dosage calculator using age-based formulas, with confidence labelling
- Alternative-medicine finder for the same condition or disease
- Inventory management with low-stock and expiry alerts
- Local backups: automatic snapshots, plus export and restore

### Custom branding

Replace the product name and logo with your own pharmacy's for a one-time
Rs 500. Open the app, go to **Branding**, and enter the licence key issued for
your pharmacy name. Keys are verified offline, so the app never needs internet.

### Windows SmartScreen

The installer is not code-signed, so Windows may show a SmartScreen warning on
first run. Click **More info** then **Run anyway**. Code signing requires a paid
certificate; ask if you would like it wired up.
"@

    $releasePayload = @{
        tag_name         = $Tag
        name             = $ReleaseName
        body             = $body
        draft            = $false
        prerelease       = $false
    } | ConvertTo-Json -Depth 5

    $apiBase = "https://api.github.com/repos/$Repo"

    # Reuse the release if this tag already exists.
    $release = $null
    try {
        $release = Invoke-RestMethod -Uri "$apiBase/releases/tags/$Tag" -Headers $headers -Method Get
        Write-Host "    release $Tag already exists - reusing it"
    } catch {
        $release = Invoke-RestMethod -Uri "$apiBase/releases" -Headers $headers -Method Post `
            -Body $releasePayload -ContentType 'application/json'
        Write-Host "    created release $Tag"
    }

    # Replace an existing asset of the same name, so re-running is safe.
    $assets = Invoke-RestMethod -Uri "$($release.upload_url -replace '\{\?.*\}', '')" `
        -Headers $headers -Method Get
    foreach ($asset in $assets) {
        if ($asset.name -eq 'PharmMS-Setup.exe') {
            Write-Host '    removing the previous asset'
            Invoke-RestMethod -Uri "$apiBase/releases/assets/$($asset.id)" `
                -Headers $headers -Method Delete | Out-Null
        }
    }

    $uploadBase = $release.upload_url -replace '\{\?.*\}', ''
    $uploadUrl = "$uploadBase" + "?name=PharmMS-Setup.exe"
    $uploadHeaders = $headers.Clone()
    $uploadHeaders['Content-Type'] = 'application/octet-stream'

    Write-Host "    uploading PharmMS-Setup.exe ($([math]::Round((Get-Item $SetupExe).Length/1MB,1)) MB)"
    Invoke-RestMethod -Uri $uploadUrl -Headers $uploadHeaders -Method Post `
        -InFile $SetupExe | Out-Null

    Write-Host '    asset uploaded'
}

# --- Summary -----------------------------------------------------------------
$setupMb = if (Test-Path $SetupExe) {
    [math]::Round((Get-Item $SetupExe).Length / 1MB, 1)
} else { 0 }

Write-Host ''
Write-Host '==============================================================' -ForegroundColor Green
Write-Host '  Published' -ForegroundColor Green
Write-Host '==============================================================' -ForegroundColor Green
Write-Host "  Repository   : https://github.com/$Repo"
if (-not $SkipRelease) {
    Write-Host "  Release      : https://github.com/$Repo/releases/tag/$Tag"
    Write-Host "  Setup file   : PharmMS-Setup.exe ($setupMb MB)"
    Write-Host ''
    Write-Host '  Share the release link. Visitors download one file and run it.'
}
Write-Host '==============================================================' -ForegroundColor Green
