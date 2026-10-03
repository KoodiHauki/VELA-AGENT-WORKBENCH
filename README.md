# Vela Agent Workbench

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Vela](https://img.shields.io/badge/Chart-Vela%20WebGL2-orange)](https://github.com/LuxAlgo/Vela)
[![FastMCP](https://img.shields.io/badge/Backend-FastMCP-green)](https://github.com/jlowin/fastmcp)
[![Pine Script](https://img.shields.io/badge/PineScript-v5%20PineTS-purple)](https://github.com/LuxAlgo/PineTS)

Paikallisesti ajettava ja Tailnetin (MagicDNS) kautta saavutettava kvantitatiivinen analyysiympäristö, jossa yhdistyvät:
- **LuxAlgo Vela (WebGL2)** -markkinakaavio suorituskykyiseen kynttilä- ja indikaattoripiirtoon.
- **Dynaaminen Pine Script v5 / PineTS** -indikaattorien generointi ja ajo suoraan selaimessa Web Workerissa.
- **FastMCP & Deterministinen Laskentamoottori** - markkinakonteksti, headless-koodivalidointi ja tilastollinen backtestaus ennen kaaviolle vientiä.
- **Antigravity 2.0 / CLI** - orkestroija ja kvanttianalyytikko luonnollisen kielen kehotteille.

```
                      +-----------------------------------+
                      |      KÄYTTÄJÄ / MOBIILI           |
                      |   (Tailnet / MagicDNS: 5173)      |
                      +-----------------+-----------------+
                                        |
                   +--------------------+--------------------+
                   |                                         |
         [WebSocket / HTTP]                         [WebGL2 Canvas]
                   |                                         |
                   v                                         v
        +---------------------+                   +---------------------+
        |  Python Bridge      |                   |  LuxAlgo Vela       |
        |  (Portti 8765)      |                   |  @luxalgo/vela      |
        +----------+----------+                   |  @luxalgo/vela-pinets|
                   |                              +----------^----------+
                   |                                         |
        +----------v----------+                              |
        |  Antigravity CLI    |                              |
        |  (Headless prosessi)|                              |
        +----------+----------+                              |
                   |                                         |
        +----------v----------+                              |
        |  FastMCP Server     +------------------------------+
        |  (server.py)        |   (push_indicator_to_chart)
        +---------------------+
```

---

## Ominaisuudet

1. **Vela WebGL2 -kaavio**: Viiveetön, erittäin suorituskykyinen kynttilärenderöinti suoralla Hyperliquid-integraatiolla.
2. **Pine Script v5 -ajuri**: `@luxalgo/vela-pinets` suorittaa indikaattorit ja strategiat taustasäikeessä (Web Worker) hidastamatta käyttöliittymää.
3. **Deterministinen Python-laskenta**: ATR, liukuvat keskiarvot, volyymiprofiilit, voittoprosentit, profit factor ja drawdown lasketaan suoraan historiadataan ilman kielimallin hallusinointeja.
4. **Headless Syntaksivalidointi**: Koodi käännetään ja validoidaan headless `pinets`-moottorilla ennen kaaviolle viemistä.
5. **Tailnet / MagicDNS -valmis**: Sovellus bindautuu kaikkiin verkkoliitäntöihin (`0.0.0.0`), ja asiakas löytää taustasillan dynaamisesti – voit ohjata analyysipöytää kännykällä Tailnetin kautta ilman porttiohjauksia.

---

## Hakemistorakenne

```
VELA-AGENT-WORKBENCH/
├── backend/
│   ├── server.py              # FastMCP-palvelin (4 kvanttityökalua Antigravitylle)
│   ├── bridge.py              # WebSocket & HTTP -silta selaimen ja CLI:n välillä
│   ├── engine.py              # Deterministinen Pandas/NumPy-analyysi ja backtest
│   ├── data_fetcher.py        # Hyperliquid REST -historiadata ja levymuisti
│   ├── validator.js           # Headless Node/PineTS -syntaksitarkistin
│   ├── mcp_config.json        # FastMCP-asetustiedosto Antigravity CLI:lle
│   └── requirements.txt       # Python-riippuvuudet (fastmcp, aiohttp, pandas jne.)
│
├── frontend/
│   ├── index.html             # Kevyt DOM-ohjattu käyttöliittymä
│   ├── package.json           # @luxalgo/vela, @luxalgo/vela-pinets, pinets, vite
│   ├── tsconfig.json
│   ├── vite.config.ts         # Vite-konfiguraatio (host: 0.0.0.0, port: 5173)
│   └── src/
│       ├── main.ts            # DOM-tapahtumakuuntelijat ja reaaliaikainen ohjaus
│       ├── chart.ts           # Vela-alustus ja PineTS-indikaattorien injektio
│       ├── hyperliquid.ts     # Hyperliquid WS & REST -asiakas
│       └── bridge_client.ts   # WS-asiakas taustasillalle
│
├── config/
│   └── system_prompt.txt      # Antigravity CLI:n kvanttianalyytikon järjestelmäkehote
├── docs/
│   └── prompt_templates.md    # Kehotepohjat ja säännöt
├── tests/
│   └── test_backend.py        # Yksikkötestit
├── run.bat                    # Windows Batch -käynnistin
└── run.ps1                    # PowerShell-käynnistin
```

---

## Pika-aloitus

### 1. Asennus
Varmista, että koneellasi on Python (>= 3.10) ja Node.js (>= 20).

```bash
# Asenna Python-riippuvuudet
python -m pip install -r backend/requirements.txt

# Asenna Frontend-riippuvuudet
npm --prefix frontend install
```

### 2. Käynnistys
Voit käynnistää järjestelmän yhdellä komennolla:

**PowerShellissä:**
```powershell
.\run.ps1
```

**Tai Windows komentokehotteessa:**
```cmd
run.bat
```

Avaa selaimessa:
- Paikallisesti: **`http://localhost:5173`**
- Tailnetin kautta: **`http://<oma-magicdns-nimi>:5173`**

---

## FastMCP-työkalut

Antigravitylle tarjotaan 4 determinististä työkalua:

1. `get_market_context(symbol: str, timeframe: str, candles: int = 100)`
   - Palauttaa ATR-volatiliteetin, trendin, liukuvat keskiarvot ja volyymin.
2. `validate_pinets_syntax(script_code: str)`
   - Kääntää koodin headless PineTS-moottorilla ja palauttaa virheen rivinumeron ja kuvauksen.
3. `run_quantitative_backtest(symbol: str, timeframe: str, strategy_rules: dict)`
   - Laskee matriisilaskennalla kauppojen määrän, voittoprosentin, tuoton ja drawdownin.
4. `push_indicator_to_chart(script_code: str, indicator_name: str)`
   - Välittää testatun indikaattorin lokaalin sillan kautta suoraan selaimen Vela-kaaviolle.

---

## Testien suoritus

Aja Python-yksikkötestit:
```powershell
python -m unittest tests/test_backend.py
```

Testaa headless syntaksitarkistin:
```powershell
node backend/validator.js "//@version=5`nindicator('Test')`nplot(close)"
```

Testaa frontendin tyyppitarkistus ja käännös:
```powershell
npm --prefix frontend run build
```
