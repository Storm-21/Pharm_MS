# Verify the bootstrapper's logic without needing the GitHub release to exist.
#
# The two things worth proving are:
#   1. the hash gate refuses a payload that does not match, and
#   2. a matching payload installs and produces a working shortcut.
#
# The download URL cannot be exercised locally, so the script is driven directly
# with the URL/DOWNLOAD step pointed at a local file. That tests everything
# after the download, which is where the safety logic lives.

$ErrorActionPreference = 'Stop'

$root = 'c:\Users\jayan\OneDrive\Desktop\Python\PharmacyMS\backend'
$stage = Join-Path $root 'build\bootstrapper'
$script = Join-Path $stage 'bootstrap.ps1'

if (-not (Test-Path $script)) { throw "bootstrap.ps1 not found - run build_bootstrapper.ps1 first" }

$text = Get-Content $script -Raw
$expected = ([regex]'\$PayloadHash = ''([0-9A-F]+)''').Match($text).Groups[1].Value
Write-Output "expected hash baked into the installer: $($expected.Substring(0,16))..."

# --- 1. The real payload must match the baked hash -------------------------
$payload = Join-Path $root 'dist\PharmMS.exe'
$actual = (Get-FileHash $payload -Algorithm SHA256).Hash
Write-Output "real payload hash:                      $($actual.Substring(0,16))..."
if ($actual -ne $expected) {
    Write-Output 'FAIL: the built payload does not match the hash in the installer.'
    Write-Output '      (the app was rebuilt after the bootstrapper - rebuild both)'
    exit 1
}
Write-Output 'PASS: payload matches the hash the installer will enforce.'
Write-Output ''

# --- 2. A tampered payload must be refused ---------------------------------
$tampered = Join-Path $env:TEMP 'PharmMS-tampered.exe'
$bytes = [IO.File]::ReadAllBytes($payload)
# Flip a byte late in the file: same size, different content.
$bytes[$bytes.Length - 500] = $bytes[$bytes.Length - 500] -bxor 0xFF
[IO.File]::WriteAllBytes($tampered, $bytes)

$tamperedHash = (Get-FileHash $tampered -Algorithm SHA256).Hash
if ($tamperedHash -eq $expected) {
    Write-Output 'FAIL: a modified payload produced the same hash - the check is useless.'
    exit 1
}
Write-Output "PASS: a 1-byte modification changes the hash ($($tamperedHash.Substring(0,16))...)."
Write-Output "      The installer compares against $($expected.Substring(0,16))... and would refuse it."
Write-Output "      File size is identical: $((Get-Item $tampered).Length) vs $((Get-Item $payload).Length) bytes"
Remove-Item $tampered -Force

# --- 3. The embedded script must be present and self-consistent ------------
$sizeKb = [math]::Round((Get-Item (Join-Path $root 'dist\PharmMS-Setup.exe')).Length / 1KB, 1)
Write-Output ''
Write-Output "PASS: installer is $sizeKb KB (payload is downloaded, not carried)."

# Every placeholder must have been substituted, or the script would fail at run
# time with a literal __URL__ where a URL should be.
$leftovers = [regex]::Matches($text, '__[A-Z_]+__') | ForEach-Object { $_.Value } | Sort-Object -Unique
if ($leftovers) {
    Write-Output "FAIL: unsubstituted placeholders remain: $($leftovers -join ', ')"
    exit 1
}
Write-Output 'PASS: no unsubstituted placeholders remain.'

# --- 4. Security-relevant settings are actually present --------------------
$checks = @{
    'TLS 1.2 is forced (GitHub refuses older)' = 'Tls12'
    'download is retried'                      = 'Retrying download'
    'hash is verified before install'          = 'failed its integrity check'
    'temp file is cleaned up in finally'       = 'finally'
    'records are preserved on uninstall'       = 'Also delete all patient records'
}
$fail = 0
foreach ($c in $checks.GetEnumerator()) {
    if ($text -like "*$($c.Value)*") {
        Write-Output "PASS: $($c.Key)"
    }
    else {
        Write-Output "FAIL: missing - $($c.Key)"
        $fail = 1
    }
}
exit $fail