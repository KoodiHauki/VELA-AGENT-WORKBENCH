#!/usr/bin/env bash
# ===================================================
#   VELA AGENT WORKBENCH - Linux / macOS Launcher
# ===================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================================="
echo "  VELA AGENT WORKBENCH - Käynnistys (Linux/macOS)"
echo "==================================================="
echo ""

# 1. Determine Python executable (prefer venv if active or present)
if [ -d "$SCRIPT_DIR/.venv" ]; then
    echo "Aktivoidaan paikallinen virtuaaliympäristö (.venv)..."
    source "$SCRIPT_DIR/.venv/bin/activate"
    PYTHON_CMD="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Virhe: Pythonia ei löytynyt. Asenna python3."
    exit 1
fi

# 2. Check Node / npm
if ! command -v npm >/dev/null 2>&1; then
    echo "Virhe: npm-komentoa ei löytynyt. Asenna Node.js (>=20) ja npm."
    exit 1
fi

# 3. Add ~/.local/bin and ~/.agy/bin to PATH if not already present
export PATH="$HOME/.local/bin:$HOME/.agy/bin:/usr/local/bin:$PATH"
export PYTHONUNBUFFERED=1
export BRIDGE_HTTP_URL="http://127.0.0.1:8765"
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/backend"

# Ensure agy MCP server is registered if agy is present
AGY_BIN=""
for candidate in "$HOME/.local/bin/agy" "$HOME/.agy/bin/agy" "/usr/local/bin/agy" "/usr/bin/agy"; do
    if [ -x "$candidate" ]; then
        AGY_BIN="$candidate"
        break
    fi
done
if [ -z "$AGY_BIN" ] && command -v agy >/dev/null 2>&1; then
    AGY_BIN="$(command -v agy)"
fi

if [ -n "$AGY_BIN" ]; then
    VENV_PY="$SCRIPT_DIR/.venv/bin/python"
    [ ! -f "$VENV_PY" ] && VENV_PY="$(command -v $PYTHON_CMD)"
    "$AGY_BIN" mcp add vela_quant "$VENV_PY" "$SCRIPT_DIR/backend/server.py" >/dev/null 2>&1 || true
fi

# 4. Start Python Bridge server in background
# Clean up any leftover bridge on port 8765 if present
if command -v fuser >/dev/null 2>&1; then
    fuser -k 8765/tcp >/dev/null 2>&1 || true
fi

echo "Käynnistetään Python WebSocket/HTTP -silta (portti 8765)..."
$PYTHON_CMD backend/bridge.py &
BRIDGE_PID=$!

# Ensure bridge process is terminated when script exits
cleanup() {
    echo ""
    echo "Sammutetaan taustasilta (PID $BRIDGE_PID)..."
    kill $BRIDGE_PID 2>/dev/null || true
    wait $BRIDGE_PID 2>/dev/null || true
    echo "Vela Agent Workbench sammutettu."
}
trap cleanup INT TERM EXIT

# Wait a moment for bridge to bind port
sleep 1

# 5. Start Vite frontend
echo "Käynnistetään Vite Frontend (portti 5173)..."
echo "Paikallinen osoite:  http://localhost:5173"
echo "Tailnet / MagicDNS:  http://$(hostname 2>/dev/null || echo '<koneesi-nimi>'):5173"
echo ""

npm --prefix frontend run dev -- --host 0.0.0.0 --port 5173
