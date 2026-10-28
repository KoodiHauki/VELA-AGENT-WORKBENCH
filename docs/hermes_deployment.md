# VELA Agent Workbench - Hermes AI & Kotiverkko -käyttöönotto

Tämä dokumentti kuvaa, kuinka **VELA Agent Workbench** on otettu käyttöön Proxmox VE:n **Hermes AI** -virtuaalikoneella (`192.168.221.189`), kuinka käänteisvälitys ja SSL-terminointi on toteutettu, sekä kuinka tulevat versiopäivitykset siirretään tuotantoon.

---

## 🌐 1. Arkkitehtuuri ja Osoitteet

Palvelu on saavutettavissa suoraan kotiverkosta (`192.168.222.0/24`) ja MikroTik Back to Home WireGuard VPN -etäyhteydellä (`192.168.216.0/24`):

* **Tuotanto-osoite (HTTPS / WSS):** [https://chart.lan.ikkala.com](https://chart.lan.ikkala.com)
* **Suora lähiverkko-osoite:** `http://192.168.221.189:5173`
* **Taustasilta (WebSocket & REST API):** `http://192.168.221.189:8765`
* **Sijainti:** Proxmox VE VM 100 (`hermes`, Ubuntu 24.04 LTS, AI VLAN 221)
* **SSL & Käänteisvälitys:** Nginx Proxy Manager (LXC 101, `192.168.222.192`, Wildcard `*.lan.ikkala.com`)
* **Nimipalvelu:** MikroTik hEX (`192.168.222.2`) staattinen DNS-ohjaus NPM:ään

---

## 🔁 2. Tulevien versioiden päivittäminen (Yhden komennon päivitys)

Kun teet muutoksia tai uusia ominaisuuksia paikalliseen työtilaan, aja projektin juuresta:

```powershell
python deploy_to_hermes.py
```

Skripti suorittaa automaattisesti:
1. Pakkaa päivitetyt tiedostot (jättäen pois `.venv`, `node_modules` ja väliaikaistiedostot).
2. Siirtää tiedostot SFTP:llä Hermekselle hakemistoon `/home/user/VELA-AGENT-WORKBENCH`.
3. Päivittää Python-riippuvuudet (`pip install -r backend/requirements.txt`).
4. Asentaa npm-riippuvuudet ja kääntää frontendin (`npm run build`).
5. Varmistaa FastMCP `vela_quant` -konfiguraation Hermeksen Antigravity-alustalle.
6. Uudelleenkäynnistää `vela-workbench.service` -systemd-palvelun.
7. Varmistaa NPM-käänteisvälityksen ja MikroTik DNS -tietueen toimivuuden.

---

## ⚙️ 3. Palvelun hallinta Hermeksellä

Voit hallita palvelua Hermes-virtuaalikoneella SSH:n kautta:

```bash
# Tarkista palvelun tila ja reaaliaikaiset lokit:
sudo systemctl status vela-workbench
journalctl -u vela-workbench -f

# Käynnistä uudelleen:
sudo systemctl restart vela-workbench

# Sammuta palvelu:
sudo systemctl stop vela-workbench
```

### Palvelun konfiguraatio (`/etc/systemd/system/vela-workbench.service`):
- **User:** `user`
- **WorkingDirectory:** `/home/user/VELA-AGENT-WORKBENCH`
- **ExecStart:** `/bin/bash /home/user/VELA-AGENT-WORKBENCH/run.sh`
- **Restart:** `always` (käynnistyy automaattisesti kaatuessa ja palvelimen uudelleenkäynnistyksessä)

---

## 🤖 4. Hermes AI -agentin käyttö

Hermes-agentti voi käyttää järjestelmää kahdella tavalla:
1. **FastMCP-työkalut (`vela_quant`):**
   - `get_market_context(symbol, timeframe, source)`: Reaaliaikaiset kynttilät ja tekniset indikaattorit.
   - `run_quantitative_backtest(symbol, timeframe, indicator_code, ...)`: Strategiatestaus.
   - `validate_pinets_syntax(code)`: Pine Script v5 / PineTS -syntaksin validointi.
   - `push_indicator_to_chart(name, code, ...)`: Indikaattorin vienti suoraan käyttäjän avoinna olevaan kaavioon.
2. **Hermes Skill (`devops/vela-workbench`):**
   - Sijainti: `/home/user/.hermes/skills/devops/vela-workbench/SKILL.md`
   - Ohjaa agenttia hallitsemaan ja käynnistämään työpöytää.
