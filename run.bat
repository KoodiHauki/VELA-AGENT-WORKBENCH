@echo off
echo ===================================================
echo   VELA AGENT WORKBENCH - Kaynnistys
echo ===================================================
echo.
echo Tarkistetaan ympayristoa ja riippuvuuksia...

REM Kaynnistetaan backend-silta taustalle
echo Kaynnistetaan Python WebSocket/HTTP -silta (portti 8765)...
start "Vela Bridge Server (8765)" cmd /k "python backend/bridge.py"

REM Kaynnistetaan Vite frontend
echo Kaynnistetaan Vite Frontend (portti 5173)...
echo.
echo Paikallinen osoite:  http://localhost:5173
echo Tailnet / MagicDNS:  Avaa selaimella koneesi Tailscale-osoite / MagicDNS-nimi portissa 5173
echo.

cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
