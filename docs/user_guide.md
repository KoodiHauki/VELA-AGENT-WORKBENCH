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
+-----------------------------------------------------------------------------------------+
| [VELA]  [Datalähde: Binance v] [Pari: BTC v] [Aika: 1h v] [Malli v] [Tila v]  [WS Dots]  |
+-------------------------------------------------------+---------------------------------+
|                                                       | [Indikaattoripyyntö: Syötä teksti] |
|                                                       | [⚡ EMA] [📊 RSI] [📈 Breakout]  |
|                                                       |                                 |
|               Vela WebGL2 -kaavio                     | [Reaaliaikainen Agenttiterminaali]|
|             (Kynttilät + Indikaattorit)               |                                 |
|                                                       | [Metriikat: WinRate, PF, DD]    |
|                                                       |                                 |
|                                                       | [Sanallinen markkinakatsaus]    |
+-------------------------------------------------------+---------------------------------+
```

### 2.1 Yläpalkin Valinnat

1. **Datalähde**:
   - `Hyperliquid`: Suora WebSocket-pörssidata ja jatkuva reaaliaikainen kynttiläpäivitys.
   - `Binance`: Globaali markkinadata (`api.binance.com`).
2. **Markkinapari**: Valitse `BTC`, `ETH`, `SOL` tai `DOGE`.
3. **Aikajänne**: Valitse kynttilävälit `1m`, `5m`, `15m`, `1h`, `4h` tai `1d`.
4. **Malli**: Valitse käytettävä tekoälymalli (`Gemini 3.8 Flash`, `Gemini 3.1 Pro`, `Claude Sonnet 4.6`).
5. **Suoritustila**:
   - `Antigravity AI (Täysi orkestrointi)`: Täysi agenttisilmukka, joka analysoi tilanteen, kirjoittaa koodin, ajaa syntaksivalidoinnin ja korjaa mahdolliset virheet itsenäisesti.
   - `Pika-analyysi (Välitön < 500ms)`: Paikallinen suora kvanttilaskenta, joka tuottaa indikaattorin, backtestaa 500 kynttilää ja piirtää sen kaaviolle välittömästi.
6. **Tilavalot**:
   - `Data WS`: Vihreä valo vahvistaa markkinadatan yhteyden.
   - `Bridge`: Vihreä valo vahvistaa yhteyden Python-taustasiltaan (portti 8765).

---

## 3. Indikaattorin Luominen ja Ajo

### 3.1 Pikavalinnat (Chips)

Voit kokeilla valmiita optimoituja indikaattoreita yhdellä klikkauksella:
- `⚡ EMA 20/50 Crossover`: Kahden eksponentiaalisen liukuvan keskiarvon dynaaminen trendi osto- ja myyntisignaaleilla.
- `📊 RSI Extreme (30/70)`: Momentumoskillaattori yliostettujen ja ylimyytyjen alueiden tunnistamiseen.
- `📈 Breakout Channel 20`: 20 kynttilän Donchian-kanavamurto tuki- ja vastustasoilla.

### 3.2 Omat Luonnollisen Kielen Pyynnöt

Kirjoita komentokenttään vapaamuotoinen pyyntö suomeksi tai englanniksi ja paina **Enter** tai klikkaa **Aja**:

**Esimerkkejä hyvistä kehotteista:**
- *"Luo nopea scalping-indikaattori 5m aikajänteelle, jossa EMA 9 ja EMA 21 risteys."*
- *"Tee RSI 14 oskillaattori, jossa dynaaminen väri kun arvo on alle 30 tai yli 70."*
- *"Rakenna 20 kynttilän kanavamurto, joka piirtää kanavan ylä- ja alareunan sekä keskilinjan."*
- *"Luo 볼 Bollinger Bands 20, 2.0 keskihajonnalla ja korosta puristustilat."*

---

## 4. Tulosten Tulkitseminen

Kun analyysi valmistuu:
1. **Kaavio**: WebGL2-kaavio piirtää uuden indikaattorin viipymättä GPU-kiihdytettynä kynttilöiden päälle tai erilliseen ruutuun.
2. **Terminaali**: Näet suoratoistona jokaisen vaiheen:
   - `[Konteksti]`: Markkinan todellinen hinta, ATR(14) -volatiliteetti, trendi ja volyymisuhde.
   - `[Validointi]`: PineTS-kääntäjän vahvistus syntaksin toimivuudesta.
   - `[Laskenta]`: 500 kynttilän simulaation tulokset.
3. **Tilastokortit**:
   - **Voittosuhde**: Voitollisten kauppojen prosenttiosuus historiassa.
   - **Profit Factor**: Bruttovoittojen suhde bruttotappioihin (arvo yli 1.5 on vahva).
   - **Drawdown**: Suurin pääoman pudotus huippuarvosta.
   - **Kaupat**: Simuloitujen kauppojen kokonaismäärä.
   - **Keskituotto / Kokonaistuotto**: Kauppakohtainen ja kumulatiivinen tuotto.
4. **Sanallinen tilannekatsaus**: Tekoäly antaa tiiviin, objektiivisen katsauksen, joka nojaa ainoastaan laskettuihin tilastoihin ilman spekulatiivisia hallusinaatioita.

---

## 5. Tailnet ja Mobiilikäyttö

Vela Agent Workbench on suunniteltu käytettäväksi suoraan älypuhelimella:
1. Käynnistä palvelin kotikoneellasi (`run.ps1`).
2. Yhdistä puhelimesi Tailscale-verkkoon.
3. Avaa puhelimen Chrome- tai Safari-selaimeen koneesi Tailscale MagicDNS -nimi portilla `5173` (esim. `http://desktop-abc:5173`).
4. Voit tarkastella WebGL2-kaaviota kosketuseleillä (zoom ja pan) ja syöttää puhelimen näppäimistöllä tai sanelulla uusia analyysipyyntöjä mistä tahansa ilman julkisia portteja.

---

## 6. Vianmääritys (Troubleshooting)

| Ongelma | Syy | Ratkaisu |
| :--- | :--- | :--- |
| **Bridge-tilavalo on harmaa / punainen** | Taustasilta (portti 8765) ei ole käynnissä tai palomuuri estää yhteyden. | Käynnistä `python backend/bridge.py` tai aja `.\run.ps1`. Varmista, ettei portti 8765 ole varattu. |
| **Kaavio ei lataa kynttilöitä** | Pörssin WebSocket tai REST -rajapinta ei vastaa. | Vaihda yläpalkista datalähdettä (esim. Hyperliquid -> Binance tai päinvastoin). |
| **Antigravity CLI ei käynnisty** | `agy` tai `antigravity` ei löydy PATH-muuttujasta. | Järjestelmä siirtyy automaattisesti käyttämään nopeaa sisäänrakennettua pika-analyysiä (`instant mode`). Voit asentaa CLI:n tai asettaa `AGY_BIN`-ympäristömuuttujan. |
| **Pine Script virhe kaaviolla** | Koodi sisältää funktioita, joita PineTS ei tue. | Antigravityn itsenäinen korjaussilmukka pyrkii korjaamaan koodin automaattisesti. Voit myös käyttää pikatilaa (`Pika-analyysi`). |
