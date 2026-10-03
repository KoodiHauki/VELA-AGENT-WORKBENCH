"""WebSocket and HTTP bridge between browser UI and Antigravity CLI / FastMCP."""

from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Set
from aiohttp import web

# Ensure backend package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import get_candles, normalize_symbol, normalize_interval
from engine import calculate_market_context, run_quantitative_backtest_logic
from server import validate_pinets_syntax

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backend.bridge")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "system_prompt.txt")
MCP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "mcp_config.json")


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
        # 1. Check environment variable
        custom_bin = os.environ.get("ANTIGRAVITY_CMD") or os.environ.get("AGY_BIN")
        if custom_bin and (os.path.exists(custom_bin) or shutil.which(custom_bin)):
            return custom_bin

        # 2. Check local AppData agy
        local_agy = os.path.expanduser(r"~\AppData\Local\agy\bin\agy.exe")
        if os.path.exists(local_agy):
            return local_agy

        # 3. Check local AppData antigravity.cmd
        local_cmd = os.path.expanduser(r"~\AppData\Local\agy\bin\antigravity.cmd")
        if os.path.exists(local_cmd):
            return local_cmd

        # 4. Check system PATH for agy or antigravity
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
                            
                            if mode == "instant":
                                asyncio.create_task(
                                    self.run_fallback_agent(ws, prompt, symbol, timeframe)
                                )
                            else:
                                asyncio.create_task(
                                    self.process_generation_request(ws, prompt, symbol, timeframe, model, effort)
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

    async def run_fallback_agent(
        self,
        ws: web.WebSocketResponse,
        user_prompt: str,
        symbol: str,
        timeframe: str,
    ):
        """Autonomous instant quant engine flow (< 500ms)."""
        await self.send_to(ws, {"type": "log", "message": f"[Pika-analyysi] Noudetaan tilastollinen konteksti parille {symbol} ({timeframe})..."})

        # 1. Context
        df = get_candles(symbol=symbol, timeframe=timeframe, bars=100)
        ctx = calculate_market_context(df)
        await self.send_to(ws, {"type": "log", "message": f"[Konteksti] {ctx.get('summary', '')}"})

        # 2. Indicator synthesis based on prompt keywords
        prompt_lower = user_prompt.lower()
        if "rsi" in prompt_lower:
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
        await self.send_to(ws, {"type": "log", "message": "[Laskenta] Suoritetaan tilastollinen backtest 500 kynttilälle..."})
        df_bt = get_candles(symbol=symbol, timeframe=timeframe, bars=500)
        metrics = run_quantitative_backtest_logic(df_bt, strategy_rule)
        metrics["symbol"] = symbol
        metrics["timeframe"] = timeframe

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
            f"Objektiivinen tilannekatsaus ({symbol} / {timeframe}): "
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
    ):
        """Run Antigravity CLI to generate and validate indicators with full event streaming."""
        await self.send_to(ws, {
            "type": "log",
            "message": f"[Komentopalkki] Vastaanotettu pyyntö: \"{user_prompt}\" (Pari: {symbol}, Aikaväli: {timeframe})",
        })

        cli_bin = self.find_antigravity_executable()
        if not cli_bin:
            logger.info("No Antigravity CLI executable found in PATH, using direct quant agent fallback.")
            await self.send_to(ws, {
                "type": "log",
                "message": "[Järjestelmä] Antigravity CLI ei saatavilla, käytetään suoraa pika-analyysiä...",
            })
            await self.run_fallback_agent(ws, user_prompt, symbol, timeframe)
            return

        logger.info("Executing Antigravity CLI via %s", cli_bin)
        await self.send_to(ws, {
            "type": "log",
            "message": f"[Antigravity] Käynnistetään AI-orkestroija (malli: {model}, effort: {effort})...",
        })

        full_prompt = (
            f"{self.system_prompt}\n\n"
            f"KÄYTTÄJÄN PYYNTÖ:\n{user_prompt}\n"
            f"Aktiivinen symboli: {symbol}, Aikajänne: {timeframe}\n"
            f"Noudata ohjeita:\n"
            f"1. Kutsu get_market_context\n"
            f"2. Kirjoita Pine Script v5 -indikaattori\n"
            f"3. Kutsu validate_pinets_syntax\n"
            f"4. Kutsu run_quantitative_backtest\n"
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

            # Stream stdout line by line
            async def read_stream(stream, is_stderr=False):
                nonlocal rendered_indicator, full_response_text
                while True:
                    line_bytes = await stream.readline()
                    if not line_bytes:
                        break
                    line = line_bytes.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    if not is_stderr:
                        try:
                            data = json.loads(line)
                            event = data.get("event")
                            if event == "step_update":
                                step = data.get("step_update", {})
                                step_type = step.get("step_type")
                                state = step.get("state")
                                
                                if step_type == "tool":
                                    tool_name = step.get("tool_name", "tuntematon")
                                    if state == "ACTIVE":
                                        await self.send_to(ws, {"type": "log", "message": f"[AI Työkalu] Kutsutaan: {tool_name}..."})
                                    elif state == "DONE":
                                        tool_info = step.get("tool_info", {})
                                        await self.send_to(ws, {"type": "log", "message": f"[AI Työkalu] {tool_name} suoritettu."})
                                        
                                        # Check if push_indicator_to_chart tool call payload is present
                                        if "push_indicator_to_chart" in str(tool_info):
                                            params = tool_info.get("parameters", {})
                                            code = params.get("script_code") or params.get("code")
                                            name = params.get("indicator_name") or params.get("name") or "Custom Indicator"
                                            if code:
                                                rendered_indicator = True
                                                await self.broadcast({"type": "render_indicator", "name": name, "code": code})
                                
                                elif step_type == "agent_response":
                                    delta = step.get("text_delta")
                                    if delta and delta.strip():
                                        full_response_text += delta
                                        # Only log meaningful non-markdown-fences fragments
                                        if not delta.startswith("```") and len(delta.strip()) > 3:
                                            await self.send_to(ws, {"type": "log", "message": delta.strip()})
                            
                            elif event == "result":
                                res = data.get("result", {})
                                resp_text = res.get("response", "")
                                if resp_text:
                                    full_response_text = resp_text
                                    await self.send_to(ws, {"type": "summary", "text": resp_text})
                            
                            else:
                                pass
                        except Exception:
                            # Not JSON, raw text log
                            await self.send_to(ws, {"type": "log", "message": line})
                    else:
                        logger.warning("CLI stderr: %s", line)
                        await self.send_to(ws, {"type": "log", "message": f"[stderr] {line}"})

            await asyncio.gather(
                read_stream(process.stdout, is_stderr=False),
                read_stream(process.stderr, is_stderr=True),
            )

            await process.wait()

            # Fallback extraction: If push_indicator_to_chart wasn't triggered, extract Pine code from text
            if not rendered_indicator and full_response_text:
                pine_match = re.search(r"```(?:pinescript|pine)?\s*(//@version=5[\s\S]*?)```", full_response_text, re.IGNORECASE)
                if not pine_match:
                    pine_match = re.search(r"(//@version=5[\s\S]*?)(?=\n\n#|\n\n---|```|$)", full_response_text)
                
                if pine_match:
                    extracted_code = pine_match.group(1).strip()
                    name_match = re.search(r'(?:indicator|strategy)\s*\(\s*["\']([^"\']+)["\']', extracted_code)
                    ind_name = name_match.group(1) if name_match else "Antigravity Indicator"
                    logger.info("Extracted Pine Script code from response: %s", ind_name)
                    await self.send_to(ws, {"type": "log", "message": f"[Kaavio] Poimittu ja toimitetaan koodi: '{ind_name}'..."})
                    await self.broadcast({
                        "type": "render_indicator",
                        "name": ind_name,
                        "code": extracted_code,
                    })

            await self.send_to(ws, {"type": "done"})

        except Exception as e:
            logger.error("CLI subprocess error: %s, falling back to direct agent", e)
            await self.send_to(ws, {"type": "log", "message": f"[CLI Virhe] {e}. Siirrytään pika-analyysiin..."})
            await self.run_fallback_agent(ws, user_prompt, symbol, timeframe)

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

        try:
            df = get_candles(symbol=symbol, timeframe=timeframe, bars=bars)
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
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
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
