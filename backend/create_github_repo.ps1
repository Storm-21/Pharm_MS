# Publish PharmMS to GitHub for the first time, in one command.
#
#   .\create_github_repo.ps1 -Repo "yourname/pharms"
#   .\create_github_repo.ps1 -Repo "yourname/pharms" -Private
#   .\create_github_repo.ps1 -Repo "yourname/pharms" -DryRun
#
# WHAT THIS SOLVES
#   publish_github.ps1 assumes the repository already exists on GitHub - it
#   pushes to it and uploads a release. On a fresh project there is nothing to
#   push to yet, and the repo has to be created, initialised and connected
#   first. This script does that part, then hands over to publish_github.ps1.
#
#   It also avoids the GitHub CLI entirely. Only `git` and a personal access
#   token are needed, because repo creation is a single REST call.
#
# REQUIREMENTS
#   * git installed (this script adds the standard install path to PATH for you)
#   * a GitHub personal access token with "repo" scope, exported as:
#         $env:GITHUB_TOKEN = "ghp_..."
#     Create one at https://github.com/settings/tokens
#
# The token is read from the environment only. It is never written to disk,
# never echoed, and never stored in the repository.

[CmdletBinding()]
param(
    # "owner/name" - the repository to create on GitHub.
    [Parameter(Mandatory = $true)]
    [string]$Repo,

    [string]$Description = 'Offline pharmacy management system for Windows - inventory, patients, prescriptions, dosing reference and printed reports.',

    [switch]$Private,

    # Create the repo and push the code, but skip building/releasing the installer.
    [switch]$SkipRelease,

    # Print every action without contacting GitHub.
    [switch]$DryRun,

    # Tag for the first release, when -SkipRelease is not passed.
    [string]$Tag = 'v2.0.0'
)

$ErrorActionPreference = 'Stop'

$ProjectDir = Split-Path $PSScriptRoot -Parent
$BackendDir = $PSScriptRoot

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }

if ($Repo -notmatch '^[^/]+/[^/]+$') {
    Fail "Repo must be in 'owner/name' form, e.g. 'jayant/pharms'. Got: '$Repo'"
}

# --- 1. Make git available ---------------------------------------------------
Write-Step 'Locating git'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    # Git for Windows is usually installed but often absent from PATH.
    foreach ($candidate in @(
        'C:\Program Files\Git\cmd',
        'C:\Program Files (x86)\Git\cmd',
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd')
    )) {
        if (Test-Path (Join-Path $candidate 'git.exe')) {
            $env:Path = "$candidate;" + $env:Path
            Write-Host "    Added $candidate to PATH for this session."
            break
        }
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail @"
git was not found.

Install Git for Windows from https://git-scm.com/download/win, then re-run.
(It normally lands in 'C:\Program Files\Git' - this script already looks there,
so a fresh install is detected without you changing PATH by hand.)
"@
}

Write-Host "    git: $(& git --version)"

# --- 2. Token ----------------------------------------------------------------
if (-not $DryRun) {
    if (-not $env:GITHUB_TOKEN) {
        Fail @"
No GITHUB_TOKEN in the environment, so the repository cannot be created.

Create a token with "repo" scope at https://github.com/settings/tokens
then set it for this session and re-run:

    `$env:GITHUB_TOKEN = "ghp_your_token_here"
    .\create_github_repo.ps1 -Repo "$Repo"
"@
    }
    Write-Host '    token present'
}

# --- 3. Make sure this is a git repository -----------------------------------
Write-Step 'Preparing the local repository'

Push-Location $ProjectDir
try {
    $inside = (& git rev-parse --is-inside-work-tree 2>&1)
    if ($inside -notmatch 'true') {
        if ($DryRun) {
            Write-Host '    [dry-run] would run: git init'
        } else {
            & git init | Out-Null
            Write-Host '    initialised a new repository'
        }
    } else {
        Write-Host '    already a git repository'
    }

    if (-not $DryRun) {
        # A commit needs an identity. Set one only if none is configured, so a
        # developer's own global identity is never overwritten.
        if (-not (& git config user.email)) {
            & git config user.email 'pharms@localhost'
            & git config user.name  'PharmMS'
            Write-Host '    set a local commit identity (none was configured)'
        }
        & git branch -M main 2>$null | Out-Null
        Write-Host '    branch is main'
    }
} finally {
    Pop-Location
}

# --- 4. Create the repository on GitHub --------------------------------------
Write-Step "Creating https://github.com/$Repo"

if ($DryRun) {
    Write-Host '    [dry-run] would POST /user/repos'
} else {
    $headers = @{
        Authorization          = "token $($env:GITHUB_TOKEN)"
        Accept                 = 'application/vnd.github+json'
        'X-GitHub-Api-Version' = '2022-11-28'
        'User-Agent'           = 'PharmMS-publisher'
    }

    $name = $Repo.Split('/')[1]

    # A repo that already exists is not an error here - publishing into an
    # existing empty repo is a normal thing to want to do.
    $existing = $null
    try {
        $existing = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo" `
            -Headers $headers -Method Get
        Write-Host "    repository already exists - reusing it"
    } catch {
        Write-Host "    repository does not exist yet - creating it"
    }

    if (-not $existing) {
        # Create under the authenticated user's account. Doing it this way, rather
        # than /orgs/$owner/repos, needs no extra permission and no knowledge of
        # whether $owner is a user or an organisation.
        $payload = @{
            name        = $name
            description = $Description
            private     = [bool]$Private
            auto_init   = $false        # we push our own history
            has_issues  = $true
            has_wiki    = $false
        } | ConvertTo-Json -Depth 4

        $created = Invoke-RestMethod -Uri 'https://api.github.com/user/repos' `
            -Headers $headers -Method Post -Body $payload -ContentType 'application/json'
        Write-Host "    created: $($created.html_url)"
    }

    # Point origin at the repo so later pushes need no arguments.
    $remoteUrl = "https://github.com/$Repo.git"
    Push-Location $ProjectDir
    try {
        $remotes = (& git remote 2>&1)
        if ($remotes -contains 'origin') {
            & git remote set-url origin $remoteUrl
            Write-Host "    origin -> $remoteUrl"
        } else {
            & git remote add origin $remoteUrl
            Write-Host "    origin added -> $remoteUrl"
        }
    } finally {
        Pop-Location
    }
}

# --- 5. Hand over to the existing publisher ----------------------------------
Write-Step 'Handing over to publish_github.ps1'

$publish = Join-Path $BackendDir 'publish_github.ps1'
if (-not (Test-Path $publish)) {
    Fail "publish_github.ps1 not found at $publish"
}

if ($DryRun) {
    Write-Host '    [dry-run] would run:'
    $skipFlag = if ($SkipRelease) { ' -SkipRelease' } else { '' }
    Write-Host ("        .\publish_github.ps1 -Repo `"$Repo`" -Tag $Tag" + $skipFlag)
    exit 0
}

Push-Location $BackendDir
try {
    if ($SkipRelease) {
        & $publish -Repo $Repo -Tag $Tag -SkipRelease
    } else {
        & $publish -Repo $Repo -Tag $Tag
    }
    if ($LASTEXITCODE -ne 0) { Fail 'publish_github.ps1 failed.' }
} finally {
    Pop-Location
}

Write-Host ''
Write-Host '==============================================================' -ForegroundColor Green
Write-Host '  Published' -ForegroundColor Green
Write-Host '==============================================================' -ForegroundColor Green
Write-Host "  Repository : https://github.com/$Repo"
if (-not $SkipRelease) {
    Write-Host "  Download   : https://github.com/$Repo/releases/latest"
    Write-Host ''
    Write-Host '  Share the download link. Visitors get PharmMS-Setup.exe and'
    Write-Host '  nothing else is needed - no Python, no Node.js, no admin rights.'
} else {
    Write-Host ''
    Write-Host '  Code pushed. Build and release later with:'
    Write-Host '      cd backend; .\build_installer.ps1'
    Write-Host "      .\publish_github.ps1 -Repo `"$Repo`" -Tag $Tag -SkipBuild"
}
Write-Host '==============================================================' -ForegroundColor Green
