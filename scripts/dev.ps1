param(
    [switch]$Install
)

if ($Install) {
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install --upgrade pip
    pip install -r backend\requirements.txt
}

if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    Write-Host "Creating venv..."
    python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload --port 8000
# Run tests: .\backend\scripts\dev.ps1 -Test

