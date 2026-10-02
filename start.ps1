$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting Sales Intelligence Platform..." -ForegroundColor Cyan

# Backend
Write-Host "  Starting backend (port 8000)..." -ForegroundColor Yellow
$backendJob = Start-Process -PassThru -NoNewWindow -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory "$root\backend"

# Frontend — find node via fnm
$fnmDir = Get-ChildItem "$env:LOCALAPPDATA\fnm_multishells" -Directory |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $fnmDir) {
    Write-Host "  ERROR: Could not find fnm node installation." -ForegroundColor Red
    exit 1
}
$npmCmd = Join-Path $fnmDir.FullName "npm.cmd"
$env:PATH = "$($fnmDir.FullName);$env:PATH"

Write-Host "  Starting frontend (port 5173)..." -ForegroundColor Yellow
$frontendJob = Start-Process -PassThru -NoNewWindow -FilePath $npmCmd `
    -ArgumentList "run", "dev" `
    -WorkingDirectory "$root\frontend"

Write-Host ""
Write-Host "Both servers starting:" -ForegroundColor Green
Write-Host "  Frontend:  http://localhost:5173"
Write-Host "  Backend:   http://localhost:8000"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers." -ForegroundColor DarkGray

try {
    while (-not $backendJob.HasExited -and -not $frontendJob.HasExited) {
        Start-Sleep -Milliseconds 500
    }
} finally {
    if (-not $backendJob.HasExited) { Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue }
    if (-not $frontendJob.HasExited) { Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Servers stopped." -ForegroundColor Yellow
}
