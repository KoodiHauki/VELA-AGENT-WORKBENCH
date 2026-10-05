# Vela Agent Workbench – Käyttöohje

Tämä opas neuvoo, miten käytät **Vela Agent Workbenchia** sujuvasti tietokoneella ja mobiililaitteella Tailnet-verkon yli.

---

## 1. Pika-aloitus ja Käynnistys

### 1.1 Palvelimen käynnistäminen

Aja projektin juurihakemistossa käynnistysskripti käyttöjärjestelmäsi mukaan:

**Linux / macOS:**
```bash
# Asenna esivaatimukset ja luo virtuaaliympäristö (ensimmäisellä kerralla):
chmod +x setup_linux.sh run.sh
./setup_linux.sh

# Käynnistä järjestelmä:
./run.sh
```

**Windows PowerShell:**
```powershell
.\run.ps1
```

**Tai Windows komentokehotteessa:**
```cmd
run.bat
```

Skripti käynnistää automaattisesti kaksi taustapalvelua:
1. **Python-taustasilta ja FastMCP-rajapinta** osoitteessa `http://0.0.0.0:8765`
2. **Vite WebGL2 -selainkäyttöliittymä** osoitteessa `http://0.0.0.0:5173`

### 1.2 Avaaminen selaimessa

- **Tällä tietokoneella**: Avaa selaimeen [http://localhost:5173](http://localhost:5173).
- **Mobiililaitteella tai toisella koneella (Tailscale / Tailnet)**:
  - Varmista, että molemmat laitteet ovat samassa Tailnet-verkossa.
  - Avaa mobiiliselaimeen: `http://<koneesi-magicdns-nimi>:5173` (esimerkiksi `http://omakone:5173`).
  - Sivusto mukautuu automaattisesti puhelimen ruudulle.

---

## 2. Käyttöliittymän Osat

```
+--------------------------------------------------------------------------------------------------------+
| [VELA]  [Datalähde: Hyperliquid v] [🔍 BTC/USD HL v] [Aika: 1h v] [Malli v] [Tila v] [📊] [💾] [💬]     |
+--------------------------------------------------------------------------------------------------------+
| ⭐ Suosikit: [⭐ BTC/USD] [⭐ ETH/USD] [⭐ SOL/USD] [⭐ BTC/USDT] ... [+ Lisää nykyinen]                |
+--------------------------------------------------------------------------------------------------------+
| Aktiiviset indikaattorit: [👁️ EMA 20/50 ✕] [👁️ RSI ✕] [Tyhjennä kaikki]                               |
+-------------------------------------------------------+------------------------------------------------+
|                                                       | 💬 Kysy kuvaajasta                             |
|                                                       | [Syötä kysymys tai pyyntö: "Aja backtest"]     |
|                                                       | [🎯 Osto/Myynti] [📍 Tasot] [⚖️ Konfluenssi]   |
|               Vela WebGL2 -kaavio                     |                                                |
|             (Kynttilät + Indikaattorit)               | 🟢 Objektiivinen Tilannekatsaus (AI Raportti)  |
|                                                       |                                                |
|                                                       | Kvantitatiiviset Metriikat (Backtest)          |
|                                                       | [Aktiivinen: EMA 20/50 + RSI] [▶️ Aja Backtest]|
|                                                       |                                                |
|                                                       | Agentin Suoritusloki (Reaaliaikainen terminaali)|
+-------------------------------------------------------+------------------------------------------------+
```

### 2.1 Yläpalkki ja Markkinaparien Haku
1. **Datalähde**:
   - `Hyperliquid`: 234 aktiivista krypto-ikifutuuria suoralla WebSocket-syötteellä.
   - `Binance Spot`: Yli 500 aktiivista USDT-kaupankäyntiparia.
   - `Arkisto (Binance Vision)`: Paikallisesti ladatut historialliset CSV-arkistot vuodesta 2017 alkaen.
2. **Markkinaparihaku (`🔍 BTC/USD ▼`)**:
   - Klikkaamalla painiketta avautuu nopea hakumodaali, josta voi etsiä mitä tahansa yli 730 saatavilla olevasta tokenista (esim. BTC, ETH, SOL, SUI, DOGE, PEPE).
   - Suodattimet: *Kaikki*, *⭐ Suosikit*, *Hyperliquid (234)*, *Binance Spot (503)*.
   - Jokaisella rivillä on tähti ⭐, jota klikkaamalla parin voi tallentaa suosikiksi tai poistaa suosikeista.
3. **⭐ Suosikkipalkki**:
   - Yläpalkin alla näkyvät tallennetut suosikkiparit (tallennus selaimen muistiin ja backend-tilaan).
   - Yhdellä klikkauksella voit vaihtaa suoraan seurattavaa markkinaa ja kaaviota.
4. **Aikajänne**: Valitse `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w` (Viikko) tai `1M` (Kuukausi).
5. **Aktiiviset indikaattorit -palkki**:
   - Kaikki kaaviolle lisätyt indikaattorit näkyvät omina merkkeinään.
   - Voit piilottaa/näyttää (`👁️` / `🙈`) tai poistaa (`✕`) yksittäisiä indikaattoreita ilman koko kaavion nollautumista.

---

## 3. "Kysy Kuvaajasta" – Tekninen Tekoälyanalyysi

Oikea sivupaneeli tarjoaa reaaliaikaisen teknisen tilannekuvan:

### 3.1 Pika-analyysipainikkeet
- **🎯 Osto vai myynti? (Bias)**: Analysoi trendin suunnan, liukuvien keskiarvojen järjestyksen (EMA 20/50, SMA 100) ja antaa objektiivisen suuntasuosituksen.
- **📍 Tuki- ja vastustasot**: Laskee viimeisimmän 100 kynttilän huiput ja pohjat sekä ATR-volatiliteettialueet.
- **⚖️ Signaalien konfluenssi**: Arvioi kaikkien ruudulla näkyvien aktiivisten indikaattoreiden ja hintatoiminnan yhteensopivuutta.
- **📈 Trendi & RSI**: Mittaa momentumin voimakkuuden ja yliostetut/ylimyydyt alueet.
- **🛡️ ATR & Stop-Loss**: Suosittelee riskinhallintatasoja ja suojavyöhykkeitä markkinan volatiliteetin perusteella.
- **📊 Volyymipoikkeamat**: Tunnistaa epätavallisen volyymin suhteessa 20 kynttilän keskiarvoon.

### 3.2 Omat Kysymykset & Intent-reititys
Voit kirjoittaa tekstikenttään minkä tahansa kysymyksen suomeksi tai englanniksi:
- *"Mikä on riskitaso, jos avaan pitkän position nyt tasolta 69 500?"*
- *"Onko havaittavissa volyymipoikkeamia tai divergenssejä?"*
- **Automaattinen Backtest-reititys**: Jos kirjoitat *"Aja EMA 20/50 backtest"* tai *"Testaa tätä strategiaa"*, järjestelmä tunnistaa pyynnön luonnollisesta kielestä ja käynnistää kvantitatiivisen backtestin suoraan.

---

## 4. Indikaattorikirjasto ja Uuden Luonti

Paina yläpalkin painiketta **📊 Indikaattorit** avataksesi kirjastomodaalin:

### 4.1 Omat Indikaattorit
- Tallennetut omat Pine Script v5 -indikaattorisi tallentuvat pysyvästi levylle (`backend/indicators/saved_indicators.json`).
- Voit lisätä minkä tahansa indikaattorin kaaviolle napilla **+ Lisää kaavioon** tai poistaa sen kirjastosta.

### 4.2 TradingView Community Scripts (10 kpl)
- Sisältää 10 suosittua ja testattua yhteisöskriptiä (mm. *Supertrend Multi-Length*, *Waddah Attar Explosion*, *Volume Flow Indicator*, *Nadaraya-Watson Envelope*).
- Voit suodattaa kategorioittain (Trendi, Oskillaattorit, Volatiliteetti, Hintatoiminta) tai hakea vapaalla tekstihaulla.

### 4.3 + Luo Uusi Indikaattori
Välilehti tarjoaa kaksi helppoa tapaa:
1. **🤖 Luo tekoälyllä (Prompt -> Pine Script v5)**:
   - Kirjoita sanallinen kuvaus tai valitse valmis pohja (*EMA 20/50 Crossover*, *RSI Extreme*, *Breakout Channel*, *Bollinger Squeeze*, *Supertrend ATR*).
   - Valitse malli ja paina **🚀 Generoi indikaattori**. Tekoäly kirjoittaa koodin, validoi syntaksin ja tuottaa koodin esikatseluun.
   - Voit testata koodia suoraan kaaviolla tai tallentaa sen kirjastoon.
2. **✏️ Kirjoita koodi manuaalisesti**:
   - Kirjoita tai liitä Pine Script v5 -koodi, anna nimi ja kuvaus ja tallenna kirjastoon.

---

## 5. Kvantitatiivinen Backtestaus & Moni-indikaattorikonfluenssi

Oikean sivupaneelin **Kvantitatiiviset Metriikat (Backtest)** -osiossa sijaitsee älykäs **`▶️ Aja Backtest`** -painike.

### 5.1 Miten Backtestaus Toimii?
1. **Yksittäinen indikaattori**:
   - Jos kaaviolla on esimerkiksi `EMA 20/50 Crossover Trend`, moottori simuloi suoraan 500 kynttilän jaksolle kultaiset ja kuoleman risteykset.
2. **Useiden indikaattoreiden samanaikainen lataus (Konfluenssi)**:
   - Jos lataat kaaviolle kaksi tai useampia indikaattoreita (esim. `EMA 20/50` + `Relative Strength Index (RSI)`), moottori yhdistää niiden ehdot:
     - **Trendi** (EMA/SMA) määrää position perussuunnan (Long vs. Short).
     - **Momentum** (RSI) suodattaa huonon markkinavaiheen sisääntulot.
     - **Kanavamurto** (Donchian/Supertrend) ajoittaa liikkeellelähdön.
3. **Molempien suuntien simulointi (Long & Short)**:
   - Järjestelmä simuloi sekä nousu- että laskumarkkinat. Jos karhumarkkinassa ensimmäisenä tulee myyntisignaali, se avaa Short-position.
4. **Metriikat**:
   - **Voittoprosentti (Win Rate)**: Voittavien kauppojen osuus.
   - **Profit Factor**: Bruttovoittojen suhde bruttotappioihin.
   - **Suurin salkkupudotus (Max Drawdown %)**: Suurin pääoman pudotus huipusta.
   - **Kauppojen määrä**: Kauppojen kokonaismäärä.
   - **Keskimääräinen tuotto**: Keskimääräinen %-tuotto per kauppa.
   - **Kokonaistuotto**: Yhteenlaskettu kumulatiivinen tuotto.

---

## 6. Yhden Käyttäjän Pysyvä Muisti (`UserMemory`)

Sovelluksessa on sisäänrakennettu tilanmuisti, joka tekee työtilasta täysin pysyvän ilman erillistä kirjautumista:

- **Mitä tallennetaan automaattisesti?**
  1. **Valittu markkina**: Viimeisin pörssi (`hyperliquid`/`binance`), pari ja aikajänne.
  2. **Suosikit (⭐)**: Kaikki tähdellä merkatut tokenit.
  3. **Kaavion aktiiviset indikaattorit**: Kaikki kaaviolle ladatut indikaattorit tallentuvat. **Kun päivität sivun (F5) tai käynnistät selaimen uudestaan, kaikki indikaattorit ladataan automaattisesti takaisin kaaviolle.**
  4. **Viimeisimmät tulokset**: Viimeksi ajetut backtest-metriikat ja tilannekatsauksen teksti säilyvät ruudulla.
- **Tallennusmekanismi**: Kaksoistallennus selaimen `localStorageen` sekä palvelimen `backend/user_state.json` -tiedostoon HTTP REST -rajapinnan kautta.

---

## 7. Täysi Historiadata (data.binance.vision)

Paina yläpalkin painiketta **💾 Historiadata**:

### 7.1 Julkisten ZIP/CSV-Arkistojen Lataus
- Binance Data Collection tarjoaa ilman kirjautumista tai API-rajoituksia kuukausikohtaiset kynttiläarkistot vuodesta 2017 alkaen.
- Valitse pari (esim. `BTCUSDT`), aikaväli (`1h`, `1d`, `1w`, `1M`), alkuvuosi ja -kuukausi sekä loppuvuosi ja -kuukausi (esim. 2023/01 – 2024/03).
- Paina **Lataa ja pura arkisto**. Palvelin lataa ZIP-paketit taustalla, purkaa CSV-tiedostot ja indeksoi ne välimuistiin.

### 7.2 📊 Avaa Kaaviolla (Arkistokatselin)
- Kaikki paikallisesti ladatut arkistot listataan taulukossa.
- Jokaisen tiedoston kohdalla on painike **📊 Avaa kaaviolla**, jota klikkaamalla kyseinen historiadata latautuu välittömästi Vela WebGL2 -kaaviolle tarkasteltavaksi!

---

## 8. Muut Julkiset Datalähteet

Järjestelmä tukee tai dokumentoi myös seuraavat rekisteröitymisvapaat julkiset rajapinnat:
- **Bybit Public Archive**: `https://public.bybit.com/kline/` (Suorat kynttilä- ja kauppa-arkistot).
- **OKX Historical REST API**: `https://www.okx.com/api/v5/market/history-candles` (Vuosien historia ilman avaimia).
- **Hyperliquid Info API**: Suora tuki jopa 5000 kynttilälle kerralla.

---

## 9. Automaattinen FastMCP-konfigurointi (`vela_quant`)

Järjestelmä sisältää automaattisen FastMCP-itsekorjautuvuuden (*self-healing auto-configuration*):
- Kun käynnistät ohjelman (`./run.sh`, `setup_linux.sh` tai `run.ps1`), taustasilta (`backend/bridge.py`) päivittää automaattisesti tiedoston `~/.gemini/config/mcp_config.json` osoittamaan aktiivisen Python-virtuaaliympäristön tulkkiin (`.venv/bin/python` tai Windowsissa `.venv\Scripts\python.exe`).
- Jos järjestelmästä löytyy Antigravity CLI (`agy`), taustasilta synkronoi rekisteröinnin suoraan CLI:lle komennolla `agy mcp add vela_quant ...`.
- Agentin käytettävissä on 6 valmista työkalua:
  1. `get_market_context`
  2. `validate_pinets_syntax`
  3. `run_quantitative_backtest`
  4. `push_indicator_to_chart`
  5. `download_historical_archive`
  6. `list_historical_archives`
- Mikäli Antigravity CLI ei ole asennettuna tai yhteys katkeaa, järjestelmä käyttää automaattista determinististä pika-analyysiä (`instant fallback`), jolloin indikaattorit, backtestit ja kaavio toimivat aina ilman katkoksia.

---

## 10. Vianmääritys ja Testaus

### 10.1 Yksikkötestien ajaminen
Varmista aina, että testit ajetaan virtuaaliympäristön Pythonilla:

**Linux / macOS:**
```bash
.venv/bin/python -m unittest tests/test_backend.py
```

**Windows PowerShell:**
```powershell
.\.venv\Scripts\python -m unittest tests/test_backend.py
```

### 10.2 Porttikonfliktit
Mikäli portti `8765` tai `5173` on varattu:
- Linux / macOS:
  ```bash
  # Etsi ja sulje porttia 8765 käyttävä vanha prosessi:
  fuser -k 8765/tcp || true
  ```
- Käynnistysskriptit (`run.sh` ja `run.ps1`) yrittävät automaattisesti vapauttaa portit ennen palveluiden käynnistämistä.

### 10.3 Headless-syntaksitarkistimen testaus
Voit testata Node.js PineTS -validaattorin suoraan komentoriviltä:
```bash
node backend/validator.js "//@version=5
indicator('Test')
plot(close)"
```
Odotettu tulos: `{"valid":true,"message":"Pine Script v5 -syntaksi ja ajo validoitu onnistuneesti."...}`
