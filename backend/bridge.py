"""WebSocket and HTTP bridge between browser UI and Antigravity CLI / FastMCP.
Supports multi-indicator analysis, chart state queries, indicators library persistence,
and Binance Data Collection historical archive downloads.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import shutil
import sys
import time
from typing import Any, Dict, List, Optional, Set
from aiohttp import web

# Ensure backend package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import get_candles, normalize_symbol, normalize_interval
from engine import calculate_market_context, run_quantitative_backtest_logic
from server import validate_pinets_syntax
from historical_downloader import (
    download_binance_range,
    list_downloaded_historical_archives,
    FREE_EXCHANGE_RESOURCES,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backend.bridge")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "system_prompt.txt")
MCP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "mcp_config.json")
INDICATORS_FILE = os.path.join(os.path.dirname(__file__), "indicators", "saved_indicators.json")


def _get_saved_indicators() -> List[Dict[str, Any]]:
    if not os.path.exists(INDICATORS_FILE):
        return []
    try:
        with open(INDICATORS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to read %s: %s", INDICATORS_FILE, e)
        return []


def _save_indicators(items: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(INDICATORS_FILE), exist_ok=True)
    with open(INDICATORS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


class BridgeServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[web.WebSocketResponse] = set()
        self.system_prompt: str = ""
        self.load_system_prompt()

    def load_system_prompt(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self.system_prompt = f.read().strip()
        else:
            self.system_prompt = (
                "Olet kvantitatiivinen analyytikko ja Pine Script -asiantuntija. "
                "Validoi aina koodi syntaksityökalulla ja testaa backtest-työkalulla."
            )

    def find_antigravity_executable(self) -> Optional[str]:
        """Find the agy / antigravity executable on this system."""
        custom_bin = os.environ.get("ANTIGRAVITY_CMD") or os.environ.get("AGY_BIN")
        if custom_bin and (os.path.exists(custom_bin) or shutil.which(custom_bin)):
            return custom_bin

        local_agy = os.path.expanduser(r"~\AppData\Local\agy\bin\agy.exe")
        if os.path.exists(local_agy):
            return local_agy

        local_cmd = os.path.expanduser(r"~\AppData\Local\agy\bin\antigravity.cmd")
        if os.path.exists(local_cmd):
            return local_cmd

        for name in ["agy", "antigravity", "gemini"]:
            which_res = shutil.which(name)
            if which_res:
                return which_res

        return None

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected browser clients."""
        if not self.clients:
            return
        payload = json.dumps(message)
        dead = set()
        for ws in self.clients:
            try:
                await ws.send_str(payload)
            except Exception:
                dead.add(ws)
        self.clients.difference_update(dead)

    async def send_to(self, ws: web.WebSocketResponse, message: Dict[str, Any]):
        try:
            await ws.send_str(json.dumps(message))
        except Exception:
            pass

    async def handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=25.0)
        await ws.prepare(request)
        self.clients.add(ws)
        client_ip = request.remote or "unknown"
        logger.info("Browser WebSocket connected from %s (Total: %d)", client_ip, len(self.clients))

        await self.send_to(ws, {
            "type": "log",
            "message": f"[Bridge] Yhteys muodostettu taustapalvelimeen ({self.host}:{self.port}).",
        })

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")

                        if msg_type == "generate_indicator":
                            prompt = data.get("prompt", "").strip()
                            symbol = normalize_symbol(data.get("symbol", "BTC"))
                            timeframe = normalize_interval(data.get("timeframe", "1h"))
                            model = data.get("model", "gemini-3.8-flash-high")
                            effort = data.get("effort", "high")
                            mode = data.get("mode", "auto")
                            source = data.get("source", "hyperliquid").lower()
                            
                            if mode == "instant":
                                asyncio.create_task(
                                    self.run_fallback_agent(ws, prompt, symbol, timeframe, source)
                                )
                            else:
                                asyncio.create_task(
                                    self.process_generation_request(ws, prompt, symbol, timeframe, model, effort, source)
                                )

                        elif msg_type == "analyze_chart":
                            # "Kysy kuvaajasta" multi-indicator technical analysis query
                            question = data.get("question", "Mikä on käyrän tilanne? Osto vai myynti?").strip()
                            snapshot = data.get("snapshot", {})
                            model = data.get("model", "gemini-3.8-flash-high")
                            effort = data.get("effort", "high")
                            mode = data.get("mode", "auto")

                            asyncio.create_task(
                                self.handle_analyze_chart(ws, question, snapshot, model, effort, mode)
                            )

                        elif msg_type == "ping":
                            await self.send_to(ws, {"type": "pong"})
                    except Exception as e:
                        logger.error("Error processing client message: %s", e)
                        await self.send_to(ws, {"type": "error", "message": str(e)})
                elif msg.type == web.WSMsgType.ERROR:
                    logger.warning("WS connection closed with error: %s", ws.exception())
        finally:
            self.clients.discard(ws)
            logger.info("Browser WebSocket disconnected (%d remaining)", len(self.clients))

        return ws

    async def handle_analyze_chart(
        self,
        ws: web.WebSocketResponse,
        question: str,
        snapshot: Dict[str, Any],
        model: str,
        effort: str,
        mode: str = "auto",
    ):
        """Technical analysis evaluation of the live chart and active indicators."""
        symbol = normalize_symbol(snapshot.get("symbol", "BTC"))
        timeframe = normalize_interval(snapshot.get("timeframe", "1h"))
        source = snapshot.get("source", "hyperliquid").lower()
        active_indicators = snapshot.get("activeIndicators", [])

        await self.send_to(ws, {
            "type": "log",
            "message": f"[Kuvaaja-analyysi] Analysoidaan käyrän tilanne: {symbol} ({timeframe}, {source.upper()}) | Kysymys: \"{question}\"...",
        })

        # 1. Fetch real market statistical context
        df = get_candles(symbol=symbol, timeframe=timeframe, bars=100, source=source)
        ctx = calculate_market_context(df)

        ind_names = [i.get("name") for i in active_indicators if i.get("visible", True)]
        ind_str = ", ".join(ind_names) if ind_names else "Ei erillisiä indikaattoreita (perushintakynttilät)"

        await self.send_to(ws, {
            "type": "log",
            "message": f"[Indikaattorit] Aktiivisena kaaviolla: {ind_str}",
        })

        # 2. Extract values safely
        price = ctx.get("current_price", 0.0)
        recent_high = ctx.get("recent_high", price)
        recent_low = ctx.get("recent_low", price)
        change_pct = ctx.get("price_change_pct", 0.0)
        atr = ctx.get("atr_14", 0.0)
        atr_pct = ctx.get("atr_pct", 0.0)
        trend_dir = ctx.get("trend_direction", "neutral")
        trend_str = ctx.get("trend_strength", "normal")
        ema20 = ctx.get("ema_20", price)
        ema50 = ctx.get("ema_50", price)
        sma100 = ctx.get("sma_100", price)
        rsi = ctx.get("rsi_14", 50.0)
        vol_ratio = ctx.get("volume_ratio", 1.0)
        vol_state = ctx.get("volume_status", "normal")

        # 3. Check if Antigravity CLI is available and mode is auto
        cli_bin = self.find_antigravity_executable()
        if cli_bin and mode == "auto":
            analysis_prompt = (
                f"Olet ammattimainen kvantitatiivinen tekninen analyytikko.\n"
                f"KÄYTTÄJÄ KYSYY KUVAJAN TILANTEESTA:\n\"{question}\"\n\n"
                f"AKTIIVINEN MARKKINATILANNE:\n"
                f"- Kohde: {symbol}\n"
                f"- Aikajänne: {timeframe}\n"
                f"- Pörssilähde: {source.upper()}\n"
                f"- Nykyhinta: {price:.2f}\n"
                f"- Jakson huippu/pohja: {recent_high:.2f} / {recent_low:.2f}\n"
                f"- Hintamuutos (100 kynttilää): {change_pct:+.2f}%\n"
                f"- ATR(14) volatiliteetti: {atr:.2f} ({atr_pct:.2f}%)\n"
                f"- Trendi: {trend_dir} (vahvuus: {trend_str})\n"
                f"- EMA 20: {ema20:.2f}, EMA 50: {ema50:.2f}, SMA 100: {sma100:.2f}\n"
                f"- RSI(14): {rsi:.1f}\n"
                f"- Volyymisuhde (viimeisin vs 20 kynttilän keskiarvo): {vol_ratio:.2f}x ({vol_state})\n\n"
                f"KAAVIOLLA AKTIIVISENA OLEVAT INDIKAATTORIT:\n"
            )
            for idx, ind in enumerate(active_indicators, start=1):
                analysis_prompt += f"{idx}. {ind.get('name')}\n"

            analysis_prompt += (
                "\nANNA STRUKTUROITU VASTAUS:\n"
                "1. **Tekninen suunta / Bias**: (🟢 OSTO / 🔴 MYYNTI / 🟡 NEUTRAALI) ja luottamustaso\n"
                "2. **Avaintasot**: Lähimmät tuki- ja vastustasot sekä ATR-suojavyöhyke (stop loss -alue)\n"
                "3. **Indikaattorien konfluenssi**: Miten aktiiviset indikaattorit ja hintatoiminta puoltavat tai vastustavat liikettä\n"
                "4. **Käytännön toimintasuositus**: Objektiivinen arvio riski/tuotto-suhteesta perustuen vain annettuihin lukuihin."
            )

            cmd = [
                cli_bin,
                "--dangerously-skip-permissions",
                "--output-format", "stream-json",
                "--effort", effort,
                "--model", model,
                "-p", analysis_prompt,
            ]

            full_response = ""
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                async def read_stream():
                    nonlocal full_response
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8", errors="replace").strip()
                        if not decoded:
                            continue
                        try:
                            evt = json.loads(decoded)
                            evt_type = evt.get("type")
                            if evt_type == "text_delta":
                                chunk = evt.get("delta", "")
                                full_response += chunk
                            elif evt_type == "final_response":
                                full_response = evt.get("response", full_response)
                        except json.JSONDecodeError:
                            full_response += decoded + "\n"

                await read_stream()
                await process.wait()

                if full_response:
                    await self.send_to(ws, {"type": "chart_analysis", "text": full_response})
                    await self.send_to(ws, {"type": "summary", "text": full_response})
                    await self.send_to(ws, {"type": "done"})
                    return
            except Exception as e:
                logger.warning("CLI technical analysis query failed, falling back to deterministic logic: %s", e)

        # Fallback / Instant deterministic analysis logic
        is_bullish = price > ema20 > ema50 and rsi > 50 and rsi < 70
        is_bearish = price < ema20 < ema50 and rsi < 50 and rsi > 30
        is_overbought = rsi >= 70
        is_oversold = rsi <= 30

        if is_overbought:
            bias = "🟡 NEUTRAALI / YLIOSTETTU (Varo laskukorjausta)"
            bias_tag = "NEUTRAL"
            action = f"RSI on voimakkaan yliostettu ({rsi:.1f}). Vältä uusien pitkien positioiden avaamista huipuilta; harkitse osavoittojen kotiuttamista tai tiukennettua stop-lossia tasolle {price - atr:.2f}."
        elif is_oversold:
            bias = "🟡 NEUTRAALI / YLIMYYTY (Mahdollinen tekninen pomppu)"
            bias_tag = "NEUTRAL"
            action = f"RSI on ylimyydyllä tasolla ({rsi:.1f}). Laskuliike voi hidastua; seuraa kääntymissignaalia ennen ostoa. Suojaustaso: {price - (atr * 1.5):.2f}."
        elif is_bullish:
            bias = "🟢 OSTO (Bullish trendijatko)"
            bias_tag = "BUY"
            action = f"Hinta ({price:.2f}) treidaa EMA 20 ({ema20:.2f}) ja EMA 50 ({ema50:.2f}) yläpuolella terveen momentumin kera (RSI {rsi:.1f}). Suositeltu tukiosto lähellä EMA 20:ta, stop-loss alle EMA 50:n ({ema50 - atr:.2f})."
        elif is_bearish:
            bias = "🔴 MYYNTI (Bearish trendijatko)"
            bias_tag = "SELL"
            action = f"Hinta ({price:.2f}) on laskutrendissä liukuvien keskiarvojen alapuolella. Suositeltu suojataso tai short-sisääntulo vastustason EMA 20 ({ema20:.2f}) lähellä."
        else:
            bias = "🟡 NEUTRAALI / KONSOLIDAATIO"
            bias_tag = "NEUTRAL"
            action = f"Markkina liikkuu vaihteluvälissä ({recent_low:.2f} - {recent_high:.2f}). Odota vahvempaa suuntaavaa signaalia tai kanavamurtoa."

        analysis_text = (
            f"### Tekninen Tilannearvio: {symbol} ({timeframe} / {source.upper()})\n\n"
            f"**Suunta / Tekninen Bias:** {bias}\n\n"
            f"**Avaintasot:**\n"
            f"- Nykyhinta: **{price:.2f}**\n"
            f"- Lähin vastus (Huippu / ATR): **{recent_high:.2f}** (alue {price + atr:.2f})\n"
            f"- Lähin tuki (EMA 20 / Pohja): **{min(ema20, price - atr):.2f}** (alue {recent_low:.2f})\n"
            f"- ATR(14) volatiliteetti: **{atr:.2f} ({atr_pct:.2f}%)**\n\n"
            f"**Indikaattorien konfluenssi ({ind_str}):**\n"
            f"- Trendi: {trend_dir.upper()} ({trend_str})\n"
            f"- Momentum (RSI 14): {rsi:.1f}\n"
            f"- Volyymi: {vol_state} ({vol_ratio:.2f}x)\n\n"
            f"**Toimintasuositus ja riskiarvio:**\n{action}"
        )

        await self.send_to(ws, {"type": "chart_analysis", "text": analysis_text, "bias": bias_tag})
        await self.send_to(ws, {"type": "summary", "text": analysis_text})
        await self.send_to(ws, {"type": "done"})

    async def run_fallback_agent(
        self,
        ws: web.WebSocketResponse,
        user_prompt: str,
        symbol: str,
        timeframe: str,
        source: str = "hyperliquid",
    ):
        """Autonomous instant quant engine flow (< 500ms)."""
        await self.send_to(ws, {"type": "log", "message": f"[Pika-analyysi] Noudetaan tilastollinen konteksti: {symbol} ({timeframe}, {source.upper()})..."})

        # 1. Context
        df = get_candles(symbol=symbol, timeframe=timeframe, bars=100, source=source)
        ctx = calculate_market_context(df)
        await self.send_to(ws, {"type": "log", "message": f"[Konteksti] {ctx.get('summary', '')}"})

        # 2. Indicator synthesis based on prompt keywords
        prompt_lower = user_prompt.lower()
        if "supertrend" in prompt_lower:
            ind_name = "SuperTrend"
            strategy_rule = {"type": "ma_crossover", "fast_period": 10, "slow_period": 30}
            pine_code = (
                "//@version=5\n"
                "indicator('SuperTrend', overlay=true)\n"
                "atr_len = input.int(10, 'ATR Length')\n"
                "factor = input.float(3.0, 'Factor')\n"
                "[supertrend, direction] = ta.supertrend(factor, atr_len)\n"
                "up = plot(direction < 0 ? supertrend : na, 'Up', color=color.green, style=plot.style_linebr, linewidth=2)\n"
                "dn = plot(direction < 0 ? na : supertrend, 'Down', color=color.red, style=plot.style_linebr, linewidth=2)\n"
            )
        elif "rsi" in prompt_lower:
            ind_name = "RSI Momentum Extreme"
            strategy_rule = {"type": "rsi", "rsi_period": 14, "oversold": 30, "overbought": 70}
            pine_code = (
                "//@version=5\n"
                f"indicator('{ind_name}', overlay=false)\n"
                "rsi_len = input.int(14, 'RSI Length')\n"
                "rsi_val = ta.rsi(close, rsi_len)\n"
                "plot(rsi_val, 'RSI', color=color.purple, linewidth=2)\n"
                "hline(70, 'Overbought', color=color.red, linestyle=hline.style_dashed)\n"
                "hline(30, 'Oversold', color=color.green, linestyle=hline.style_dashed)\n"
                "hline(50, 'Midline', color=color.gray, linestyle=hline.style_dotted)\n"
            )
        elif "breakout" in prompt_lower or "donchian" in prompt_lower or "kanava" in prompt_lower:
            ind_name = "Breakout Channel 20"
            strategy_rule = {"type": "breakout", "lookback": 20}
            pine_code = (
                "//@version=5\n"
                f"indicator('{ind_name}', overlay=true)\n"
                "len = input.int(20, 'Channel Length')\n"
                "upper = ta.highest(high, len)\n"
                "lower = ta.lowest(low, len)\n"
                "basis = (upper + lower) / 2\n"
                "plot(upper, 'Upper Band', color=color.teal, linewidth=2)\n"
                "plot(lower, 'Lower Band', color=color.maroon, linewidth=2)\n"
                "plot(basis, 'Midline', color=color.gray, style=plot.style_line)\n"
            )
        else:
            ind_name = "EMA 20/50 Dynamic Trend"
            strategy_rule = {"type": "ma_crossover", "fast_period": 20, "slow_period": 50, "ma_mode": "ema"}
            pine_code = (
                "//@version=5\n"
                f"indicator('{ind_name}', overlay=true)\n"
                "fast_len = input.int(20, 'Fast EMA')\n"
                "slow_len = input.int(50, 'Slow EMA')\n"
                "fast_ema = ta.ema(close, fast_len)\n"
                "slow_ema = ta.ema(close, slow_len)\n"
                "bull_cross = ta.crossover(fast_ema, slow_ema)\n"
                "bear_cross = ta.crossunder(fast_ema, slow_ema)\n"
                "plot(fast_ema, 'Fast EMA', color=color.new(#00e676, 0), linewidth=2)\n"
                "plot(slow_ema, 'Slow EMA', color=color.new(#ff1744, 0), linewidth=2)\n"
                "plotshape(bull_cross, 'Buy Signal', location=location.belowbar, color=color.green, style=shape.triangleup, size=size.small)\n"
                "plotshape(bear_cross, 'Sell Signal', location=location.abovebar, color=color.red, style=shape.triangledown, size=size.small)\n"
            )

        await self.send_to(ws, {"type": "log", "message": f"[Generointi] Luotu Pine Script v5: '{ind_name}'"})

        # 3. Validate
        await self.send_to(ws, {"type": "log", "message": "[Validointi] Tarkistetaan syntaksi headless PineTS -moottorilla..."})
        val = validate_pinets_syntax(pine_code)
        if not val.get("valid"):
            await self.send_to(ws, {"type": "log", "message": f"[Syntaksivirhe] Rivi {val.get('line')}: {val.get('error')}"})
            return

        await self.send_to(ws, {"type": "log", "message": "[Validointi] Pine Script v5 -syntaksi hyväksytty!"})

        # 4. Backtest
        await self.send_to(ws, {"type": "log", "message": f"[Laskenta] Suoritetaan tilastollinen backtest 500 kynttilälle ({source.upper()})..."})
        df_bt = get_candles(symbol=symbol, timeframe=timeframe, bars=500, source=source)
        metrics = run_quantitative_backtest_logic(df_bt, strategy_rule)
        metrics["symbol"] = symbol
        metrics["timeframe"] = timeframe
        metrics["source"] = source

        await self.send_to(ws, {"type": "metrics", "data": metrics})
        await self.send_to(ws, {"type": "log", "message": f"[Backtest Metriikat] {metrics.get('summary', '')}"})

        # 5. Push to chart
        await self.send_to(ws, {"type": "log", "message": f"[Kaavio] Renderöidään indikaattori '{ind_name}' Vela-kaaviolle..."})
        await self.broadcast({
            "type": "render_indicator",
            "name": ind_name,
            "code": pine_code,
        })

        # 6. Summary
        summary = (
            f"Objektiivinen tilannekatsaus ({symbol} / {timeframe} / {source.upper()}): "
            f"Hinta {ctx['current_price']:.2f}, trendi {ctx['trend_direction']} ({ctx['trend_strength']}), "
            f"ATR volatiliteetti {ctx['atr_pct']}%. Indikaattorin '{ind_name}' historiallinen voittosuhde on "
            f"{metrics['win_rate']}% ({metrics['trades_count']} kauppaa), profit factor {metrics['profit_factor']} "
            f"ja max drawdown {metrics['max_drawdown_pct']}%."
        )
        await self.send_to(ws, {"type": "summary", "text": summary})
        await self.send_to(ws, {"type": "done"})

    async def process_generation_request(
        self,
        ws: web.WebSocketResponse,
        user_prompt: str,
        symbol: str,
        timeframe: str,
        model: str,
        effort: str,
        source: str = "hyperliquid",
    ):
        """Run Antigravity CLI to generate and validate indicators with full event streaming."""
        await self.send_to(ws, {
            "type": "log",
            "message": f"[Komentopalkki] Vastaanotettu pyyntö: \"{user_prompt}\" (Pari: {symbol}, Aikaväli: {timeframe}, Lähde: {source.upper()})",
        })

        cli_bin = self.find_antigravity_executable()
        if not cli_bin:
            logger.info("No Antigravity CLI executable found in PATH, using direct quant agent fallback.")
            await self.send_to(ws, {
                "type": "log",
                "message": "[Järjestelmä] Antigravity CLI ei saatavilla, käytetään suoraa pika-analyysiä...",
            })
            await self.run_fallback_agent(ws, user_prompt, symbol, timeframe, source)
            return

        logger.info("Executing Antigravity CLI via %s", cli_bin)
        await self.send_to(ws, {
            "type": "log",
            "message": f"[Antigravity] Käynnistetään AI-orkestroija (malli: {model}, effort: {effort})...",
        })

        full_prompt = (
            f"{self.system_prompt}\n\n"
            f"KÄYTTÄJÄN PYYNTÖ:\n{user_prompt}\n"
            f"Aktiivinen symboli: {symbol}, Aikajänne: {timeframe}, Markkinalähde: {source}\n"
            f"Noudata ohjeita:\n"
            f"1. Kutsu get_market_context(symbol='{symbol}', timeframe='{timeframe}', source='{source}')\n"
            f"2. Kirjoita Pine Script v5 -indikaattori\n"
            f"3. Kutsu validate_pinets_syntax(script_code=...)\n"
            f"4. Kutsu run_quantitative_backtest(symbol='{symbol}', timeframe='{timeframe}', strategy_rules=..., source='{source}')\n"
            f"5. Kutsu push_indicator_to_chart\n"
            f"6. Tulosta analyyttinen yhteenveto ja koodi."
        )

        cmd = [
            cli_bin,
            "--dangerously-skip-permissions",
            "--output-format", "stream-json",
            "--effort", effort,
            "--model", model,
            "-p", full_prompt,
        ]

        rendered_indicator = False
        full_response_text = ""

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def read_stream():
                nonlocal rendered_indicator, full_response_text
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace").strip()
                    if not decoded:
                        continue

                    try:
                        evt = json.loads(decoded)
                        evt_type = evt.get("type")

                        if evt_type == "step_start":
                            step_title = evt.get("title") or evt.get("name") or "Agentin vaihe"
                            await self.send_to(ws, {"type": "log", "message": f"[Vaihe] {step_title}"})

                        elif evt_type == "step_update":
                            step_type = evt.get("step_type", "")
                            if step_type == "tool":
                                tool_name = evt.get("tool_name", "työkalu")
                                args = evt.get("arguments", {})
                                await self.send_to(ws, {
                                    "type": "log",
                                    "message": f"[Työkalukutsu] {tool_name}({json.dumps(args)[:100]})",
                                })

                        elif evt_type == "text_delta":
                            chunk = evt.get("delta", "")
                            full_response_text += chunk

                        elif evt_type == "final_response":
                            full_response_text = evt.get("response", full_response_text)
                            await self.send_to(ws, {"type": "summary", "text": full_response_text})

                    except json.JSONDecodeError:
                        await self.send_to(ws, {"type": "log", "message": decoded})

            await read_stream()
            await process.wait()

            # Regex fallback extraction if push_indicator_to_chart wasn't invoked via tool call
            if not rendered_indicator and "//@version=5" in full_response_text:
                match = re.search(r"```(?:pinescript|pine)?\s*(//@version=5[\s\S]*?)```", full_response_text)
                if match:
                    extracted_code = match.group(1).strip()
                    logger.info("Extracted Pine Script from markdown response")
                    await self.send_to(ws, {
                        "type": "log",
                        "message": "[Järjestelmä] Löydetty Pine Script v5 -koodi vastauksesta. Renderöidään kaaviolle...",
                    })
                    await self.broadcast({
                        "type": "render_indicator",
                        "name": "Generated Indicator",
                        "code": extracted_code,
                    })

            await self.send_to(ws, {"type": "done"})

        except Exception as e:
            logger.error("Error running Antigravity CLI: %s", e)
            await self.send_to(ws, {
                "type": "log",
                "message": f"[Virhe] Antigravity CLI epäonnistui: {e}. Käytetään pika-analyysiä...",
            })
            await self.run_fallback_agent(ws, user_prompt, symbol, timeframe, source)

    # HTTP REST Handlers
    async def handle_push_indicator(self, request: web.Request) -> web.Response:
        """HTTP POST endpoint for FastMCP push_indicator_to_chart."""
        try:
            data = await request.json()
            name = data.get("name", "Custom Indicator")
            code = data.get("code", "")
            if not code:
                return web.json_response({"error": "Missing indicator code"}, status=400)

            logger.info("Broadcasting push_indicator: %s", name)
            await self.broadcast({
                "type": "render_indicator",
                "name": name,
                "code": code,
            })
            return web.json_response({"status": "ok", "delivered_to": len(self.clients)})
        except Exception as e:
            logger.error("Error in handle_push_indicator: %s", e)
            return web.json_response({"error": str(e)}, status=500)

    async def handle_push_metrics(self, request: web.Request) -> web.Response:
        """HTTP POST endpoint for FastMCP backtest metrics forwarding."""
        try:
            data = await request.json()
            await self.broadcast({
                "type": "metrics",
                "data": data,
            })
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_get_candles(self, request: web.Request) -> web.Response:
        """HTTP GET endpoint for candle snapshots."""
        symbol = request.query.get("symbol", "BTC")
        timeframe = request.query.get("timeframe", "1h")
        bars = int(request.query.get("bars", 1000))
        source = request.query.get("source", "hyperliquid")

        try:
            df = get_candles(symbol=symbol, timeframe=timeframe, bars=bars, source=source)
            records = []
            for _, row in df.iterrows():
                records.append({
                    "openTime": int(row["time_ms"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                })
            return web.json_response({"symbol": symbol, "timeframe": timeframe, "candles": records})
        except Exception as e:
            logger.error("Failed to fetch candles via API: %s", e)
            return web.json_response({"error": str(e)}, status=500)

    # Indicator persistence endpoints
    async def handle_get_indicators(self, request: web.Request) -> web.Response:
        indicators = _get_saved_indicators()
        return web.json_response({"status": "ok", "indicators": indicators})

    async def handle_save_indicator(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            name = data.get("name", "").strip()
            code = data.get("code", "").strip()
            if not name or not code:
                return web.json_response({"error": "Nimi ja koodi vaaditaan."}, status=400)

            items = _get_saved_indicators()
            ind_id = data.get("id") or f"ind_{int(time.time() * 1000)}"

            # Update existing or add new
            existing_idx = next((i for i, item in enumerate(items) if item.get("id") == ind_id), None)
            new_item = {
                "id": ind_id,
                "name": name,
                "description": data.get("description", ""),
                "category": data.get("category", "Omat"),
                "author": data.get("author", "Käyttäjä"),
                "createdAt": data.get("createdAt", int(time.time() * 1000)),
                "code": code,
            }

            if existing_idx is not None:
                items[existing_idx] = new_item
            else:
                items.append(new_item)

            _save_indicators(items)
            return web.json_response({"status": "ok", "indicator": new_item})
        except Exception as e:
            logger.error("Failed to save indicator: %s", e)
            return web.json_response({"error": str(e)}, status=500)

    async def handle_delete_indicator(self, request: web.Request) -> web.Response:
        ind_id = request.match_info.get("id")
        if not ind_id:
            return web.json_response({"error": "Missing indicator id"}, status=400)

        items = _get_saved_indicators()
        new_items = [i for i in items if i.get("id") != ind_id]
        _save_indicators(new_items)
        return web.json_response({"status": "ok", "deleted": ind_id})

    # Historical data archive endpoints
    async def handle_download_historical(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            symbol = data.get("symbol", "BTCUSDT")
            interval = data.get("interval", "1h")
            start_year = int(data.get("start_year", 2024))
            start_month = int(data.get("start_month", 1))
            end_year = int(data.get("end_year", 2024))
            end_month = int(data.get("end_month", 1))

            res = download_binance_range(symbol, interval, start_year, start_month, end_year, end_month)
            return web.json_response({"status": "ok", "result": res})
        except Exception as e:
            logger.error("Historical download failed: %s", e)
            return web.json_response({"error": str(e)}, status=500)

    async def handle_list_historical(self, request: web.Request) -> web.Response:
        archives = list_downloaded_historical_archives()
        return web.json_response({
            "status": "ok",
            "archives": archives,
            "free_resources": FREE_EXCHANGE_RESOURCES,
        })

    async def handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({
            "status": "healthy",
            "service": "vela-agent-bridge",
            "clients_connected": len(self.clients),
        })


def create_app() -> web.Application:
    server = BridgeServer()
    app = web.Application()

    # CORS middleware
    async def cors_middleware(app, handler):
        async def middleware(request):
            if request.method == "OPTIONS":
                response = web.Response()
            else:
                response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return response
        return middleware

    app.middlewares.append(cors_middleware)

    # Routes
    app.router.add_get("/", server.handle_ws)
    app.router.add_get("/ws", server.handle_ws)
    app.router.add_post("/api/push_indicator", server.handle_push_indicator)
    app.router.add_post("/api/push_metrics", server.handle_push_metrics)
    app.router.add_get("/api/candles", server.handle_get_candles)
    app.router.add_get("/api/indicators", server.handle_get_indicators)
    app.router.add_post("/api/indicators", server.handle_save_indicator)
    app.router.add_delete("/api/indicators/{id}", server.handle_delete_indicator)
    app.router.add_post("/api/historical/download", server.handle_download_historical)
    app.router.add_get("/api/historical/list", server.handle_list_historical)
    app.router.add_get("/api/health", server.handle_health)

    return app


def main():
    app = create_app()
    port = int(os.environ.get("BRIDGE_PORT", 8765))
    host = os.environ.get("BRIDGE_HOST", "0.0.0.0")
    logger.info("Starting Vela-Agent-Workbench Bridge server on http://%s:%d", host, port)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    main()
