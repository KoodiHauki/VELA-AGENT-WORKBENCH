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

echo ""
echo "==================================================="
echo "  Asennus onnistui! Kaikki riippuvuudet asennettu."
echo "==================================================="
echo ""
echo "Voit nyt käynnistää ohjelman komennolla:"
echo "  chmod +x run.sh && ./run.sh"
echo ""
