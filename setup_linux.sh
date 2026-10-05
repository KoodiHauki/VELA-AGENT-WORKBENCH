#!/usr/bin/env bash
# ===================================================
#   VELA AGENT WORKBENCH - Linux Setup & Asennus
# ===================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================================="
echo "  VELA AGENT WORKBENCH - Linux Asennusskripti"
echo "==================================================="
echo ""

echo "=== 1. Tarkistetaan esivaatimukset ==="
if ! command -v python3 >/dev/null 2>&1; then
    echo "Virhe: python3 puuttuu. Asenna:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    echo "  Fedora:        sudo dnf install -y python3 python3-pip"
    echo "  Arch Linux:    sudo pacman -S python python-pip"
    exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo "Virhe: node tai npm puuttuu. Asenna Node.js >= 20 ja npm."
    echo "  Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs"
    echo "  Tai nvm:       nvm install 20"
    exit 1
fi

echo "Python: $(python3 --version)"
echo "Node:   $(node --version)"
echo "npm:    $(npm --version)"

echo ""
echo "=== 2. Luodaan Python-virtuaaliympäristö (.venv) ==="
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtuaaliympäristö luotu kansioon .venv"
else
    echo "Virtuaaliympäristö .venv on jo olemassa."
fi
source .venv/bin/activate

echo ""
echo "=== 3. Asennetaan Python-riippuvuudet ==="
pip install --upgrade pip
pip install -r backend/requirements.txt

echo ""
echo "=== 4. Asennetaan Frontend-riippuvuudet (npm) ==="
npm --prefix frontend install

echo ""
echo "=== 5. Testataan frontendin tuotantokäännös ==="
npm --prefix frontend run build

# 6. Auto-register FastMCP tool with Antigravity
echo ""
echo "=== 6. Konfiguroidaan FastMCP-työkalu Antigravitylle (vela_quant) ==="
mkdir -p "$HOME/.gemini/config"
GLOBAL_MCP="$HOME/.gemini/config/mcp_config.json"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
SERVER_SCRIPT="$SCRIPT_DIR/backend/server.py"

# Write or update ~/.gemini/config/mcp_config.json with absolute paths
python3 -c "
import json, os
cfg_path = os.path.expanduser('~/.gemini/config/mcp_config.json')
data = {'mcpServers': {}}
if os.path.exists(cfg_path):
    try:
        with open(cfg_path, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict) or 'mcpServers' not in data:
                data = {'mcpServers': {}}
    except Exception:
        data = {'mcpServers': {}}
data['mcpServers']['vela_quant'] = {
    'command': '$VENV_PYTHON',
    'args': ['$SERVER_SCRIPT'],
    'env': {
        'PYTHONUNBUFFERED': '1',
        'PYTHONPATH': '$SCRIPT_DIR:$SCRIPT_DIR/backend',
        'BRIDGE_HTTP_URL': 'http://127.0.0.1:8765'
    },
    'disabled': False
}
with open(cfg_path, 'w') as f:
    json.dump(data, f, indent=2)
print('Kirjoitettu globaali MCP-konfiguraatio:', cfg_path)
" || true

# Also sync with agy CLI if found in PATH or standard user directories
export PATH="$HOME/.local/bin:$HOME/.agy/bin:/usr/local/bin:$PATH"
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
    echo "Löydetty Antigravity CLI: $AGY_BIN"
    "$AGY_BIN" mcp add vela_quant "$VENV_PYTHON" "$SERVER_SCRIPT" || true
    echo "FastMCP vela_quant rekisteröity Antigravity CLI:lle."
else
    echo "Huom: 'agy' komentoa ei vielä löytynyt PATH:sta, mutta globaali konfiguraatio tallennettu (~/.gemini/config/mcp_config.json)."
fi

echo ""
echo "=== 7. Suoritetaan järjestelmän itsetestit ==="
$VENV_PYTHON -c "import fastmcp, aiohttp, pandas, requests; print('✔ Python-riippuvuudet ja FastMCP kunnossa!')"
$VENV_PYTHON -c "from backend.engine import calculate_market_context, run_quantitative_backtest_logic; print('✔ Kvanttimoottori ja backtest-logiikka kunnossa!')"
node backend/validator.js <<< "//@version=5\nindicator('Test')\nplot(close)" >/dev/null 2>&1 && echo "✔ Headless Node.js PineTS -validaattori kunnossa!" || echo "ℹ Node.js validaattori valinnainen (Python-fallback käytössä)."

echo ""
echo "==================================================="
echo "  Asennus onnistui! Kaikki komponentit valmiina."
echo "==================================================="
echo ""
echo "Voit nyt käynnistää järjestelmän komennolla:"
echo "  ./run.sh"
echo ""
