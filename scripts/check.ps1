$ErrorActionPreference = "Stop"

Write-Host "Running SkillBridge checks..." -ForegroundColor Cyan

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "`n[1/4] Validate documentation files"
$required = @(
    "README.md",
    "docs/PRODUCT_SPEC.md",
    "docs/DATA_MODEL.md",
    "docs/USER_RESEARCH_PLAN.md",
    "docs/ROADMAP.md",
    "docs/RUNNING_LOCALLY.md"
)
foreach ($file in $required) {
    if (-not (Test-Path $file)) {
        throw "Missing required file: $file"
    }
}

Write-Host "`n[2/4] Python tests"
& $python -m unittest discover -s backend/tests -v
if ($LASTEXITCODE -ne 0) { throw "Python tests failed" }

Write-Host "`n[3/4] Python and frontend checks"
& $python -m compileall -q backend/app
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed" }
node --check frontend/app.js
if ($LASTEXITCODE -ne 0) { throw "Frontend syntax check failed" }
node --check frontend/three-scene.js
if ($LASTEXITCODE -ne 0) { throw "3D scene syntax check failed" }
node --test frontend/tests/scene.test.js
if ($LASTEXITCODE -ne 0) { throw "3D scene tests failed" }

Write-Host "`n[4/4] Git whitespace check"
if (Test-Path ".git") {
    git diff --check
    if ($LASTEXITCODE -ne 0) {
        throw "Git whitespace check failed"
    }
} else {
    Write-Host "Git repository not initialized yet; skipped."
}

Write-Host "`nAll checks passed." -ForegroundColor Green
