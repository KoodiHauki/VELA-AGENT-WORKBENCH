# Vela Agent Workbench – API- ja Työkalureferenssi

Tämä dokumentti määrittelee FastMCP-työkalujen, taustasillan HTTP REST -rajapintojen ja WebSocket-protokollan täydelliset määritykset, parametrit ja vastaukset.

---

## 1. FastMCP-työkalut (`backend/server.py`)

Nämä työkalut rekisteröidään FastMCP-protokollan kautta ja ovat käytettävissä Antigravity CLI:lle (`agy`) tai mille tahansa MCP-yhteensopivalle agentille.

### 1.1 `get_market_context`

Hakee markkinan tilastollisen yhteenvedon ja faktapohjaisen tilannekuvan.

**Parametrit:**
| Nimi | Tyyppi | Oletus | Kuvaus |
| :--- | :--- | :--- | :--- |
| `symbol` | `string` | `"BTC"` | Markkinakolikko (esim. `"BTC"`, `"ETH"`, `"SOL"`). |
| `timeframe` | `string` | `"1h"` | Aikaväli (`"1m"`, `"5m"`, `"15m"`, `"1h"`, `"4h"`, `"1d"`). |
| `candles` | `integer` | `100` | Analysoitavien historiabaarien määrä. |
| `source` | `string` | `"hyperliquid"` | Datalähdepörssi: `"hyperliquid"` tai `"binance"`. |

**Palautusarvo (`dict`):**
```json
{
  "symbol": "BTC",
  "timeframe": "1h",
  "source": "binance",
  "current_price": 84872.01,
  "high_period": 85037.63,
  "low_period": 84232.01,
  "change_pct": 2.18,
  "atr_14": 122.82,
  "atr_pct": 0.14,
  "trend_direction": "bullish",
  "trend_strength": "moderate",
  "ema_20": 84836.14,
  "ema_50": 84787.56,
  "sma_100": 84650.12,
  "rsi_14": 51.0,
  "volume_ratio": 0.11,
  "volume_state": "below_average",
  "summary": "Price is at 84872.01 (+2.18% over 100 bars). Trend is bullish (moderate). EMA20: 84836.14, EMA50: 84787.56. ATR(14) is 122.82 (0.14% vol). RSI(14) is 51.0. Volume ratio is 0.11x (below_average). Range high: 85037.63, low: 84232.01."
}
```

---

### 1.2 `validate_pinets_syntax`

Kääntää ja validoi Pine Script v5 / PineTS -koodin headless-taustaprosessissa ennen sen suorittamista selaimessa.

**Parametrit:**
| Nimi | Tyyppi | Kuvaus |
| :--- | :--- | :--- |
| `script_code` | `string` | Validoitava Pine Script v5 / PineTS -lähdekoodi. |

**Onnistunut palautus (`dict`):**
```json
{
  "valid": true,
  "message": "Pine Script v5 -syntaksi ja ajo validoitu onnistuneesti.",
  "transpiledLines": 42
}
```

**Virheellinen palautus (`dict`):**
```json
{
  "valid": false,
  "error": "Failed to transpile Pine Script version 5: Unexpected token EOF '' at 5:1",
  "line": 5
}
```

---

### 1.3 `run_quantitative_backtest`

Suorittaa deterministisen kvantitatiivisen backtestin 500 kynttilän historiadataan käyttäen määriteltyjä strategiasääntöjä.

**Parametrit:**
| Nimi | Tyyppi | Oletus | Kuvaus |
| :--- | :--- | :--- | :--- |
| `symbol` | `string` | - | Markkinapari (esim. `"BTC"`). |
| `timeframe` | `string` | - | Kynttilöiden aikaväli (esim. `"1h"`). |
| `strategy_rules` | `dict` | - | Strategiasäännöt (katso alla tuetut tyypit). |
| `source` | `string` | `"hyperliquid"` | Datalähdepörssi (`"hyperliquid"` tai `"binance"`). |

**Tuetut strategiatyypit (`strategy_rules`):**
1. **Liukuvien keskiarvojen risteys (`ma_crossover`)**:
   ```json
   {
     "type": "ma_crossover",
     "fast_period": 20,
     "slow_period": 50,
     "ma_mode": "ema"
   }
   ```
2. **RSI-momentum (`rsi`)**:
   ```json
   {
     "type": "rsi",
     "rsi_period": 14,
     "oversold": 30,
     "overbought": 70
   }
   ```
3. **Kanavamurto (`breakout` tai `donchian`)**:
   ```json
   {
     "type": "breakout",
     "lookback": 20
   }
   ```
4. **Monen indikaattorin konfluenssi (`multi_confluence`)**:
   Kun kaaviolla on useita aktiivisia indikaattoreita (esim. `EMA 20/50` + `RSI` + `Donchian`), moottori yhdistää niiden signaalit monen ehdon konfluenssimalliksi. Trendi antaa pääsuunnan, oskillaattori (RSI) vahvistaa momentumin ja kanavamurto ajoittaa sisääntulon. Tukee sekä Long- että Short-positioita.


**Palautusarvo (`dict`):**
```json
{
  "strategy": "ma_crossover",
  "trades_count": 8,
  "win_rate": 75.0,
  "winning_trades": 6,
  "losing_trades": 2,
  "avg_return_pct": 3.42,
  "total_return_pct": 27.36,
  "profit_factor": 2.85,
  "max_drawdown_pct": 4.12,
  "summary": "Kvantitatiivinen backtest (ma_crossover): 8 kauppaa, voittoprosentti 75.0%, keskimääräinen tuotto +3.42%, kokonaistuotto +27.36%, profit factor 2.85, suurin salkkupudotus (drawdown) 4.12%.",
  "symbol": "BTC",
  "timeframe": "1h",
  "source": "binance"
}
```

---

### 1.4 `push_indicator_to_chart`

Lähettää hyväksytyn ja testatun indikaattorikoodin lokaalin HTTP-rajapinnan kautta aktiiviseen selaimeen.

**Parametrit:**
| Nimi | Tyyppi | Oletus | Kuvaus |
| :--- | :--- | :--- | :--- |
| `script_code` | `string` | - | Validi Pine Script v5 / PineTS -koodi. |
| `indicator_name` | `string` | `"Custom Indicator"` | Indikaattorille annettava selkeä nimi. |

**Palautusarvo (`dict`):**
```json
{
  "success": true,
  "message": "Indikaattori 'EMA 20/50 Dynamic Trend' lähetetty onnistuneesti Vela-kaaviolle."
}
```

---

### 1.5 `download_historical_archive`

Lataa kuukausikohtaiset kynttiläarkistot suoraan rekisteröitymisvapaasta `data.binance.vision` -julkisesta arkistosta valitulle aikavälille, purkaa ZIP-paketit CSV-tiedostoiksi ja tallentaa ne paikalliseen levyvälimuistiin.

**Parametrit:**
| Nimi | Tyyppi | Oletus | Kuvaus |
| :--- | :--- | :--- | :--- |
| `symbol` | `string` | `"BTCUSDT"` | Kaupankäyntipari (esim. `"BTCUSDT"`, `"ETHUSDT"`). |
| `interval` | `string` | `"1h"` | Kynttilöiden aikaväli (`"1m"`, `"5m"`, `"15m"`, `"1h"`, `"4h"`, `"1d"`, `"1w"`, `"1M"`). |
| `start_year` | `integer` | `2024` | Alkuvuosi (esim. `2023`). |
| `start_month` | `integer` | `1` | Alkukuukausi (`1`-`12`). |
| `end_year` | `integer` | `2024` | Loppuvuosi (esim. `2024`). |
| `end_month` | `integer` | `1` | Loppukuukausi (`1`-`12`). |
| `exchange` | `string` | `"binance"` | Julkinen arkistolähde (`"binance"` -> data.binance.vision). |

**Palautusarvo (`dict`):**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "status": "completed",
  "downloaded_files": [
    "BTCUSDT-1h-2024-01.csv",
    "BTCUSDT-1h-2024-02.csv"
  ],
  "total_rows": 1440,
  "start_date": "2024-01-01 00:00:00",
  "end_date": "2024-02-29 23:00:00"
}
```

---

### 1.6 `list_historical_archives`

Listaa kaikki levylle ladatut, puretut ja välimuistissa olevat historialliset kynttiläarkistot sekä niiden tiedostokoot, rivimäärät ja aikaleimat.

**Parametrit:** Ei vaadi parametreja.

**Palautusarvo (`list`):**
```json
[
  {
    "symbol": "BTCUSDT",
    "interval": "1d",
    "filename": "BTCUSDT-1d-2024-01.csv",
    "path": "/home/user/VELA-AGENT-WORKBENCH/backend/.cache/historical/binance/BTCUSDT/1d/BTCUSDT-1d-2024-01.csv",
    "size_bytes": 4512,
    "rows": 31,
    "start_time": 1704067200000,
    "end_time": 1706659200000
  }
]
```

---

## 2. Taustasillan HTTP REST -rajapinnat (`portti 8765`)

Siltapalvelin tarjoaa HTTP REST -rajapintoja paikallista tiedonvälitystä ja tilatarkistuksia varten.

### `POST /api/push_indicator`
Vastaanottaa indikaattorin ja lähettää sen WebSocket-lähetyksenä (broadcast) kaikille avoimille selaimille.
- **Pyyntö (JSON):**
  ```json
  {
    "name": "EMA 20/50",
    "code": "//@version=5\nindicator('EMA 20/50')...\n"
  }
  ```
- **Vastaus:** `{"status": "ok", "delivered_to": 1}`

### `POST /api/push_metrics`
Vastaanottaa backtest-metriikat ja päivittää ne reaaliaikaisesti selaimen tilastokortteihin.
- **Pyyntö (JSON):** Backtest-metriikkaobjekti.
- **Vastaus:** `{"status": "ok"}`

### `GET /api/symbols`
Palauttaa saatavilla olevat pörssiparit (Hyperliquid 234 kpl, Binance Spot 503 kpl) levyvälimuistista tai suoralla haulla.
- **Kyselyparametrit:**
  - `source`: `"all"`, `"hyperliquid"` tai `"binance"`
  - `refresh`: `true` tai `false` (pakotettu päivitys pörssirajapinnoista)
- **Vastaus (JSON):**
  ```json
  {
    "status": "ok",
    "source": "all",
    "count": 737,
    "symbols": [
      {
        "symbol": "BTC",
        "pair": "BTC/USD",
        "base": "BTC",
        "quote": "USD",
        "source": "hyperliquid",
        "maxLeverage": 40
      },
      {
        "symbol": "BTCUSDT",
        "pair": "BTC/USDT",
        "base": "BTC",
        "quote": "USDT",
        "source": "binance"
      }
    ]
  }
  ```

### `GET /api/candles`
Noutaa kynttilähistorian JSON-muodossa live-pörsseistä tai paikallisesta Binance Vision -arkistosta.
- **Kyselyparametrit:**
  - `symbol`: e.g. `BTC` tai `BTCUSDT`
  - `timeframe`: e.g. `1h`, `1d`, `1w`, `1M`
  - `bars`: e.g. `100` (oletus `1000`)
  - `source`: `"hyperliquid"`, `"binance"` tai `"archive"`
  - `file`: (valinnainen kun `source=archive`) tietty ladattu CSV-tiedosto, esim. `BTCUSDT-1h-2024-01.csv`
- **Vastaus (JSON):**
  ```json
  {
    "symbol": "BTC",
    "timeframe": "1h",
    "source": "hyperliquid",
    "candles": [
      {
        "openTime": 1727985600000,
        "open": 84500.0,
        "high": 85100.0,
        "low": 84300.0,
        "close": 84872.0,
        "volume": 1240.5
      }
    ]
  }
  ```

### `POST /api/historical/download`
Lataa ja purkaa kynttiläarkiston `data.binance.vision` -arkistosta valitulle aikavälille.
- **Pyyntö (JSON):**
  ```json
  {
    "symbol": "BTCUSDT",
    "interval": "1h",
    "start_year": 2024,
    "start_month": 1,
    "end_year": 2024,
    "end_month": 3
  }
  ```

### `GET /api/historical/list`
Listaa kaikki levylle ladatut ja puretut historialliset CSV-arkistot sekä tiedot muista rekisteröitymisvapaista julkisista arkistoista (Bybit, OKX).

### `POST /api/backtest`
Suorittaa deterministisen kvantitatiivisen backtestin välittömästi ilman WebSocket-riippuvuutta. Tunnistaa kaaviolla aktiivisena olevat indikaattorit ja muodostaa niistä automaattisesti konfluenssistrategian.
- **Pyyntö (JSON):**
  ```json
  {
    "symbol": "BTC",
    "timeframe": "1h",
    "source": "hyperliquid",
    "rules": {},
    "activeIndicators": [
      {
        "name": "EMA 20/50 Crossover Trend",
        "code": "//@version=5\nindicator('EMA 20/50 Crossover Trend')...\n"
      },
      {
        "name": "Relative Strength Index (RSI)",
        "code": "//@version=5\nindicator('RSI')...\n"
      }
    ]
  }
  ```
- **Vastaus (JSON):**
  ```json
  {
    "status": "ok",
    "strategy": "Konfluenssi: EMA 20/50 Crossover Trend + Relative Strength Index (RSI)",
    "metrics": {
      "trades_count": 14,
      "win_rate": 21.4,
      "winning_trades": 3,
      "losing_trades": 11,
      "avg_return_pct": 0.08,
      "total_return_pct": 1.14,
      "profit_factor": 1.18,
      "max_drawdown_pct": 3.82,
      "summary": "..."
    },
    "summary": "### Kvantitatiivinen Backtest: Konfluenssi...\n\n- Kauppojen määrä: 14..."
  }
  ```

### `GET /api/user-state` ja `POST /api/user-state`
Yhden käyttäjän pysyvä tilamuisti (`backend/user_state.json`), joka tallentaa ja palauttaa työtilan tilan palvelimen ja selaimen välillä.
- **Tallennettavat kentät:**
  - `selectedMarket`: Symboli, aikajänne, lähde ja näyttönimi.
  - `favoriteKeys`: Suosikkiparien tunnisteet (esim. `["hyperliquid:BTC", "binance:BTCUSDT"]`).
  - `activeIndicators`: Kaaviolle ladattujen aktiivisten indikaattoreiden koodit ja nimet (palautetaan automaattisesti käynnistyksessä).
  - `lastBacktest`: Viimeisimmät lasketut metriikat ja sanallinen yhteenveto.
  - `lastAnalysis`: Viimeisin tekninen tilannearvio ja osto/myynti-bias.

### `GET /api/health`
Palvelimen terveydentila ja aktiivisten asiakkaiden määrä.
- **Vastaus:** `{"status": "healthy", "service": "vela-agent-bridge", "clients_connected": 1}`

---

## 3. Taustasillan WebSocket-protokolla (`ws://<host>:8765/ws`)

Kaikki reaaliaikainen vuorovaikutus selaimen ja taustajärjestelmän välillä kulkee WebSocketin kautta JSON-muodossa.

### 3.1 Selaimelta palvelimelle (Client -> Server)

#### `analyze_chart` (Kysy kuvaajasta)
Lähettää kaavion tilannekuvan ja käyttäjän teknisen kysymyksen analysoitavaksi:
```json
{
  "type": "analyze_chart",
  "question": "Mikä on tämänhetkinen tilanne? Onko osto vai myynti?",
  "snapshot": {
    "symbol": "BTC",
    "timeframe": "60",
    "source": "hyperliquid",
    "activeIndicators": [
      { "id": "ind_1", "name": "EMA 20/50", "visible": true }
    ]
  },
  "model": "gemini-3.8-flash-high",
  "effort": "high",
  "mode": "auto"
}
```

#### `generate_indicator`
Käynnistää indikaattorin analysoinnin, koodauksen ja testauksen.
```json
{
  "type": "generate_indicator",
  "prompt": "Luo RSI 14 indikaattori osto- ja myyntisignaaleilla",
  "symbol": "BTC",
  "timeframe": "1h",
  "model": "gemini-3.8-flash-high",
  "effort": "high",
  "mode": "auto",
  "source": "binance"
}
```

#### `run_backtest`
Suorittaa reaaliaikaisen kvantitatiivisen backtestin WebSocket-virran yli hyödyntäen kaaviolla aktiivisena olevia indikaattoreita (konfluenssi) tai määriteltyjä strategiasääntöjä:
```json
{
  "type": "run_backtest",
  "symbol": "BTC",
  "timeframe": "1h",
  "source": "hyperliquid",
  "rules": {},
  "activeIndicators": [
    {
      "id": "ind_1",
      "name": "EMA 20/50 Crossover Trend",
      "code": "//@version=5\nindicator('EMA 20/50')...\n",
      "visible": true
    }
  ]
}
```

#### `ping`
Yhteyden elossapito. Palvelin vastaa `{"type": "pong"}`.

---

### 3.2 Palvelimelta selaimelle (Server -> Client)

| Tyyppi (`type`) | Sisältö | Kuvaus |
| :--- | :--- | :--- |
| `log` | `{"message": "..."}` | Rivi agentin suoratoistoterminaaliin. |
| `metrics` | `{"data": { ... }}` | Backtest-metriikat tilastokorttien päivitykseen. |
| `render_indicator`| `{"name": "...", "code": "..."}` | Pine Script v5 -koodi ajettavaksi Vela-kaaviolle. |
| `summary` | `{"text": "..."}` | Agentin objektiivinen sanallinen tilannekatsaus. |
| `done` | `{}` | Kertoo ajon päättymisestä ja vapauttaa komentopalkin. |
| `error` | `{"message": "..."}` | Virheilmoitus. |

---

## 4. Laskentakaavat ja Metriikat

1. **ATR(14) (Average True Range)**:
   $$\text{TR}_t = \max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)$$
   $$\text{ATR}_t = \text{EMA}_{14}(\text{TR})$$
   $$\text{ATR}\% = \frac{\text{ATR}_t}{C_t} \times 100$$
2. **Voittoprosentti (Win Rate)**:
   $$\text{Win Rate} = \frac{\text{Voittavat kaupat}}{\text{Kauppojen kokonaismäärä}} \times 100\%$$
3. **Profit Factor**:
   $$\text{Profit Factor} = \frac{\sum \text{Bruttovoitot}}{\sum |\text{Bruttotappiot}|}$$
4. **Suurin salkkupudotus (Max Drawdown %)**:
   $$\text{DD}_t = \frac{\text{Huippuarvo} - \text{Nykyarvo}}{\text{Huippuarvo}} \times 100\%$$
   $$\text{Max Drawdown} = \max(\text{DD}_t)$$
