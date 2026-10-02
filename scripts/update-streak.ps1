# Regenerate docs/STREAK.md from real git history.
#
# Designed to be safe to run unattended from Windows Task Scheduler:
#   - It only READS git history. It never writes, commits, or pushes.
#   - It stores no credentials and touches no secrets.
#   - It exits 0 even when the streak is broken, because a broken streak is a
#     real result, not a failure of this script.
#
# Pushing stays a human decision on purpose. A scheduled task that committed
# and pushed would need a token on disk, and a token on disk is exactly the
# thing this repository refuses to have.

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$report = Join-Path $repo "docs\STREAK.md"
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"

Write-Host "Updating streak report..."
& $python (Join-Path $repo "scripts\streak.py") --repo $repo --weeks 14 --write $report
if ($LASTEXITCODE -ne 0) {
    # A non-zero exit means the tracker could not read history at all. Surface
    # it loudly, because a silently stale report is worse than no report.
    Write-Host "Streak tracker could not read git history." -ForegroundColor Red
    exit 1
}

$stats = & $python (Join-Path $repo "scripts\streak.py") --repo $repo --json | ConvertFrom-Json
Write-Host ""
Write-Host "Current streak : $($stats.streak) day(s)"
Write-Host "Longest streak : $($stats.longest) day(s)"
Write-Host "Total commits  : $($stats.total_commits)"
Write-Host "Last commit    : $($stats.last_commit) ($($stats.days_since_last) day(s) ago)"

if ($stats.streak -eq 0) {
    Write-Host ""
    Write-Host "Streak is broken. Ship something real today rather than editing the report." -ForegroundColor Yellow
}
