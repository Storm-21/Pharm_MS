# PharmMS desktop installer.
#
#   .\install_app.ps1                install for the current user
#   .\install_app.ps1 -Uninstall     remove the app and its shortcuts
#   .\install_app.ps1 -KeepData      uninstall but keep the database
#
# Installs to %LOCALAPPDATA%\Programs\PharmMS (no admin rights needed) and
# creates shortcuts on the Desktop and in the Start Menu.
#
# The database is NOT stored in the install folder. It lives in
# %LOCALAPPDATA%\PharmMS, so uninstalling, reinstalling or upgrading the app
# never touches your records.

[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$KeepData
)

$ErrorActionPreference = 'Stop'

$AppName    = 'Pharmacy Management System'
$ShortName  = 'PharmMS'
$SourceExe  = Join-Path $PSScriptRoot 'dist\PharmMS.exe'
$InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\PharmMS'
$DataDir    = Join-Path $env:LOCALAPPDATA 'PharmMS'
$DesktopDir = [Environment]::GetFolderPath('Desktop')
$StartMenu  = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'

function Write-Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }

function New-Shortcut($path, $target, $workdir, $icon) {
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($path)
    $link.TargetPath = $target
    $link.WorkingDirectory = $workdir
    if ($icon) { $link.IconLocation = $icon }
    $link.Description = $AppName
    $link.Save()
}

# ---------------------------------------------------------------- uninstall --
if ($Uninstall) {
    Write-Step 'Removing shortcuts'
    foreach ($lnk in @(
        (Join-Path $DesktopDir "$ShortName.lnk"),
        (Join-Path $DesktopDir "$AppName.lnk"),
        (Join-Path $StartMenu "$ShortName.lnk")
    )) {
        if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Host "    removed $lnk" }
    }

    Write-Step 'Removing installed files'
    if (Test-Path $InstallDir) {
        Remove-Item $InstallDir -Recurse -Force
        Write-Host "    removed $InstallDir"
    }

    if ($KeepData) {
        Write-Host ''
        Write-Host "  Your data was kept at: $DataDir" -ForegroundColor Green
    } else {
        $answer = Read-Host "Also delete all patient records in $DataDir ? Type DELETE to confirm"
        if ($answer -eq 'DELETE') {
            Remove-Item $DataDir -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host '    records deleted'
        } else {
            Write-Host "    records kept at $DataDir"
        }
    }

    Write-Host ''
    Write-Host 'Uninstalled.' -ForegroundColor Green
    exit 0
}

# ------------------------------------------------------------------ install --
if (-not (Test-Path $SourceExe)) {
    Write-Host "ERROR: $SourceExe not found." -ForegroundColor Red
    Write-Host 'Build it first:  .\build_exe.ps1'
    exit 1
}

Write-Step "Installing to $InstallDir"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Close a running copy so the file is not locked.
Get-Process $ShortName -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host '    closing a running copy...'
    $_.CloseMainWindow() | Out-Null
    Start-Sleep -Milliseconds 800
    if (-not $_.HasExited) { $_.Kill() }
}

Copy-Item $SourceExe (Join-Path $InstallDir "$ShortName.exe") -Force
Write-Host '    application files copied'

$target = Join-Path $InstallDir "$ShortName.exe"

Write-Step 'Creating shortcuts'
New-Shortcut (Join-Path $DesktopDir "$ShortName.lnk") $target $InstallDir $target
Write-Host "    Desktop:   $DesktopDir\$ShortName.lnk"
New-Shortcut (Join-Path $StartMenu "$ShortName.lnk") $target $InstallDir $target
Write-Host "    Start Menu: $StartMenu\$ShortName.lnk"

$sizeMb = [math]::Round((Get-Item $target).Length / 1MB, 1)

Write-Host ''
Write-Host '==============================================================' -ForegroundColor Green
Write-Host '  Installed' -ForegroundColor Green
Write-Host '==============================================================' -ForegroundColor Green
Write-Host "  Launch from the Desktop shortcut '$ShortName'"
Write-Host "  or from the Start Menu."
Write-Host ''
Write-Host "  Program : $target  ($sizeMb MB)"
Write-Host "  Records : $DataDir\pharmacy.db"
Write-Host ''
Write-Host '  Your records live outside the install folder, so'
Write-Host '  reinstalling or upgrading never loses data.'
Write-Host '==============================================================' -ForegroundColor Green
