# Evidentia-AI Backend Startup Script for Windows PowerShell
$port = if ($env:PORT) { $env:PORT } else { "8000" }
$workers = if ($env:WORKERS) { $env:WORKERS } else { "1" }
$env:ENVIRONMENT = if ($env:ENVIRONMENT) { $env:ENVIRONMENT } else { "production" }
$env:DISABLE_EMBEDDED_WORKER = "false"

# Locate virtual environment Python and Uvicorn
$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
$venvUvicorn = Join-Path $PSScriptRoot "venv\Scripts\uvicorn.exe"

$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }
$uvicornExe = if (Test-Path $venvUvicorn) { $venvUvicorn } else { "uvicorn" }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EVIDENTIA-AI FORENSIC BACKEND SERVER (WINDOWS)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[EVIDENTIA-AI] Python Binary: $pythonExe" -ForegroundColor Gray
Write-Host "[EVIDENTIA-AI] Port: $port | Workers: $workers" -ForegroundColor Gray
Write-Host "[EVIDENTIA-AI] Starting ASGI Server at http://127.0.0.1:$port..." -ForegroundColor Green

& $uvicornExe app:app --host 127.0.0.1 --port $port --workers $workers
