# Vela Agent Workbench – Käyttöohje

Tämä opas neuvoo, miten käytät **Vela Agent Workbenchia** sujuvasti tietokoneella ja mobiililaitteella Tailnet-verkon yli.

---

## 1. Pika-aloitus ja Käynnistys

### 1.1 Palvelimen käynnistäminen

Aja projektin juurihakemistossa käynnistysskripti:

**Windows PowerShell:**
```powershell
.\run.ps1
```

**Tai Windows komentokehote:**
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
| Aktiiviset indikaattorit: [👁️ EMA 20/50 ✕] [👁️ RSI Extreme ✕] [Tyhjennä kaikki]                       |
+-------------------------------------------------------+------------------------------------------------+
|                                                       | 💬 Kysy kuvaajasta                             |
|                                                       | [Syötä kysymys: "Mikä on käyrän tilanne?"]     |
|                                                       | [🎯 Osto/Myynti] [📍 Tasot] [⚖️ Konfluenssi]   |
|               Vela WebGL2 -kaavio                     |                                                |
|             (Kynttilät + Indikaattorit)               | Objektiivinen Tilannekatsaus (AI Raportti)     |
|                                                       |                                                |
|                                                       | Kvantitatiiviset Metriikat (Backtest)          |
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
   - Yläpalkin alla näkyvät tallennetut suosikkiparit (tallennus selaimen `localStorageen`).
   - Yhdellä klikkauksella voit vaihtaa suoraan seurattavaa markkinaa ja kaaviota.
4. **Aikajänne**: Valitse `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w` (Viikko) tai `1M` (Kuukausi).
5. **Aktiiviset indikaattorit -palkki**:
   - Kaikki kaaviolle lisätyt indikaattorit näkyvät omina merkkeinään.
   - Voit piilottaa/näyttää (`👁️` / `🙈`) tai poistaa (`✕`) yksittäisiä indikaattoreita ilman, että koko kaavio nollautuu.

---

## 3. "Kysy Kuvaajasta" – Tekninen Tekoälyanalyysi

Oikea sivupaneeli on omistettu tekniselle analyysille ja interaktiiviselle kyselylle:

### 3.1 Pika-analyysipainikkeet
- **🎯 Osto vai myynti? (Bias)**: Analysoi trendin suunnan, liukuvien keskiarvojen järjestyksen (EMA 20/50, SMA 100) ja antaa objektiivisen suuntasuosituksen.
- **📍 Tuki- ja vastustasot**: Laskee viimeisimmän 100 kynttilän huiput ja pohjat sekä ATR-volatiliteettialueet.
- **⚖️ Signaalien konfluenssi**: Arvioi kaikkien ruudulla näkyvien aktiivisten indikaattoreiden ja hintatoiminnan yhteensopivuutta.
- **📈 Trendi & RSI**: Mittaa momentumin voimakkuuden ja yliostetut/ylimyydyt alueet.
- **🛡️ ATR & Stop-Loss**: Suosittelee riskinhallintatasoja ja suojavyöhykkeitä markkinan volatiliteetin perusteella.

### 3.2 Omat Kysymykset
Voit kirjoittaa tekstikenttään minkä tahansa kysymyksen suomeksi tai englanniksi:
- *"Mikä on riskitaso, jos avaan pitkän position nyt tasolta 69 500?"*
- *"Onko havaittavissa volyymipoikkeamia tai divergenssejä?"*

---

## 4. Indikaattorikirjasto ja Uuden Luonti

Paina yläpalkin painiketta **📊 Indikaattorit** avataksesi kirjastomodaalin:

### 4.1 Omat Indikaattorit
- Tallennetut omat Pine Script v5 -indikaattorisi tallentuvat pysyvästi levylle (`backend/indicators/saved_indicators.json`).
- Voit lisätä minkä tahansa indikaattorin kaaviolle napilla **+ Lisää kaavioon** tai poistaa sen kirjastosta.

### 4.2 TradingView Community Scripts (10 kpl)
- Sisältää 10 suosittua ja testattua yhteisöskriptiä (mm. *Supertrend Multi-Length*, *Waddah Attar Explosion*, *Volume Flow Indicator*, *Nadaraya-Watson Envelope*).
- Voit suodattaa kategorioittain (Trendi, Oskillaattorit, Volatiliteetti, Hintatoiminta) tai hakea vapaalla tekstipohjaisella haulla.

### 4.3 + Luo Uusi Indikaattori
Välilehti tarjoaa kaksi helppoa tapaa:
1. **🤖 Luo tekoälyllä (Prompt -> Pine Script v5)**:
   - Kirjoita sanallinen kuvaus tai valitse valmis pohja (*EMA 20/50 Crossover*, *RSI Extreme*, *Breakout Channel*, *Bollinger Squeeze*, *Supertrend ATR*).
   - Valitse malli ja paina **🚀 Generoi indikaattori**. Tekoäly kirjoittaa koodin, validoi syntaksin ja tuottaa koodin esikatseluun.
   - Voit testata koodia suoraan kaaviolla tai tallentaa sen kirjastoon.
2. **✏️ Kirjoita koodi manuaalisesti**:
   - Kirjoita tai liitä Pine Script v5 -koodi, anna nimi ja kuvaus ja tallenna kirjastoon.

---

## 5. Täysi Historiadata (data.binance.vision)

Paina yläpalkin painiketta **💾 Historiadata**:

### 5.1 Julkisten ZIP/CSV-Arkistojen Lataus
- Binance Data Collection tarjoaa ilman kirjautumista tai API-rajoituksia kuukausikohtaiset kynttiläarkistot vuodesta 2017 alkaen.
- Valitse pari (esim. `BTCUSDT`), aikaväli (`1h`, `1d`, `1w`, `1M`), alkuvuosi ja -kuukausi sekä loppuvuosi ja -kuukausi (esim. 2023/01 – 2024/03).
- Paina **Lataa ja pura arkisto**. Palvelin lataa ZIP-paketit taustalla, purkaa CSV-tiedostot ja indeksoi ne välimuistiin.

### 5.2 📊 Avaa Kaaviolla (Arkistokatselin)
- Kaikki paikallisesti ladatut arkistot listataan taulukossa.
- Jokaisen tiedoston kohdalla on painike **📊 Avaa kaaviolla**, jota klikkaamalla kyseinen historiadata latautuu välittömästi Vela WebGL2 -kaaviolle tarkasteltavaksi!

---

## 6. Muut Julkiset Datalähteet

Järjestelmä tukee tai dokumentoi myös seuraavat rekisteröitymisvapaat julkiset rajapinnat:
- **Bybit Public Archive**: `https://public.bybit.com/kline/` (Suorat kynttilä- ja kauppa-arkistot).
- **OKX Historical REST API**: `https://www.okx.com/api/v5/market/history-candles` (Vuosien historia ilman avaimia).
- **Hyperliquid Info API**: Suora tuki jopa 5000 kynttilälle kerralla.
