$ErrorActionPreference = "Stop"

Write-Host "Running SkillBridge checks..." -ForegroundColor Cyan

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "`n[1/3] Validate documentation files"
$required = @(
    "README.md",
    "docs/PRODUCT_SPEC.md",
    "docs/DATA_MODEL.md",
    "docs/USER_RESEARCH_PLAN.md",
    "docs/ROADMAP.md"
)
foreach ($file in $required) {
    if (-not (Test-Path $file)) {
        throw "Missing required file: $file"
    }
}

Write-Host "`n[2/3] Python syntax check"
if (Test-Path "backend") {
    & $python -m compileall -q backend 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Python compilation failed"
    }
} else {
    Write-Host "Backend not created yet; documentation foundation only."
}

Write-Host "`n[3/3] Git whitespace check"
if (Test-Path ".git") {
    git diff --check
    if ($LASTEXITCODE -ne 0) {
        throw "Git whitespace check failed"
    }
} else {
    Write-Host "Git repository not initialized yet; skipped."
}

Write-Host "`nAll checks passed." -ForegroundColor Green
