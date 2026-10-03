# PowerShell launcher for Vela Agent Workbench

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  VELA AGENT WORKBENCH - Kaynnistys" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# Ensure PATH includes agy
$agyPath = "$env:LOCALAPPDATA\agy\bin"
if (Test-Path $agyPath) {
    if (-not ($env:Path -split ";" -contains $agyPath)) {
        $env:Path = "$agyPath;$env:Path"
    }
}

Write-Host "Kaynnistetaan Python WebSocket/HTTP -silta (portti 8765)..." -ForegroundColor Yellow
$bridgeProcess = Start-Process python -ArgumentList "backend/bridge.py" -PassThru

Write-Host "Kaynnistetaan Vite Frontend (portti 5173)..." -ForegroundColor Green
Write-Host "Paikallinen osoite: http://localhost:5173" -ForegroundColor Green
Write-Host "Tailnet / MagicDNS: Avaa esim. selaimella Tailscale MagicDNS-nimi portissa 5173" -ForegroundColor Green
Write-Host ""

try {
    npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173
}
finally {
    if ($bridgeProcess -and -not $bridgeProcess.HasExited) {
        Write-Host "Sammutetaan taustasilta..." -ForegroundColor Gray
        Stop-Process -Id $bridgeProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
