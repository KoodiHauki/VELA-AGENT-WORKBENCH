/**
 * Application Entry Point: DOM controls, event bindings, and live orchestrations.
 */

import { VelaChartManager } from './chart';
import { BridgeClient, BacktestMetrics } from './bridge_client';

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const chartContainer = document.getElementById('chart-container') as HTMLElement;
  const promptInput = document.getElementById('prompt-input') as HTMLInputElement;
  const sendBtn = document.getElementById('send-btn') as HTMLButtonElement;
  const symbolSelect = document.getElementById('symbol-select') as HTMLSelectElement;
  const timeframeSelect = document.getElementById('timeframe-select') as HTMLSelectElement;
  const modelSelect = document.getElementById('model-select') as HTMLSelectElement;
  const effortSelect = document.getElementById('effort-select') as HTMLSelectElement;
  const bridgeDot = document.getElementById('bridge-status-dot') as HTMLElement;
  const hlDot = document.getElementById('hl-status-dot') as HTMLElement;
  const terminal = document.getElementById('agent-terminal') as HTMLElement;
  const clearTermBtn = document.getElementById('clear-term-btn') as HTMLButtonElement;
  const agentSummary = document.getElementById('agent-summary') as HTMLElement;
  const presetChips = document.querySelectorAll('.preset-chip');

  // Metrics elements
  const metricWinrate = document.getElementById('metric-winrate') as HTMLElement;
  const metricPf = document.getElementById('metric-pf') as HTMLElement;
  const metricDd = document.getElementById('metric-dd') as HTMLElement;
  const metricTrades = document.getElementById('metric-trades') as HTMLElement;
  const metricAvgret = document.getElementById('metric-avgret') as HTMLElement;
  const metricTotret = document.getElementById('metric-totret') as HTMLElement;

  function appendLog(message: string) {
    if (!terminal) return;
    const line = document.createElement('div');
    line.className = 'terminal-line';

    if (message.includes('[Virhe]') || message.includes('error') || message.includes('Error')) {
      line.classList.add('error');
    } else if (message.includes('[Validointi]') || message.includes('onnistuneesti') || message.includes('OK')) {
      line.classList.add('success');
    } else if (message.includes('[Järjestelmä]') || message.includes('[Bridge]')) {
      line.classList.add('info');
    } else if (message.includes('[Korjaus]')) {
      line.classList.add('warning');
    }

    line.textContent = message;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
  }

  function updateMetrics(m: BacktestMetrics) {
    if (metricWinrate) metricWinrate.textContent = `${m.win_rate.toFixed(1)}%`;
    if (metricPf) metricPf.textContent = `${m.profit_factor.toFixed(2)}`;
    if (metricDd) metricDd.textContent = `${m.max_drawdown_pct.toFixed(2)}%`;
    if (metricTrades) metricTrades.textContent = `${m.trades_count}`;
    if (metricAvgret) metricAvgret.textContent = `${m.avg_return_pct >= 0 ? '+' : ''}${m.avg_return_pct.toFixed(2)}%`;
    if (metricTotret && m.total_return_pct !== undefined) {
      metricTotret.textContent = `${m.total_return_pct >= 0 ? '+' : ''}${m.total_return_pct.toFixed(2)}%`;
    }
  }

  // 1. Initialize Vela Chart
  const initialSymbol = symbolSelect.value || 'BTC';
  const initialTimeframe = timeframeSelect.value || '1h';
  const chartManager = new VelaChartManager(chartContainer);

  try {
    chartManager.init(initialSymbol, initialTimeframe);
    if (hlDot) {
      hlDot.classList.add('online');
    }
    appendLog(`[Järjestelmä] Vela WebGL2 -kaavio alustettu parille ${initialSymbol} (${initialTimeframe}).`);
  } catch (err) {
    appendLog(`[Virhe] Vela-kaavion alustus epäonnistui: ${err}`);
  }

  // 2. Initialize Bridge Client
  const bridgeClient = new BridgeClient();

  bridgeClient.onLog = (msg: string) => {
    appendLog(msg);
  };

  bridgeClient.onMetrics = (metrics: BacktestMetrics) => {
    updateMetrics(metrics);
  };

  bridgeClient.onRenderIndicator = async (name: string, code: string) => {
    appendLog(`[Kaavio] Vastaanotettu indikaattori "${name}". Piirretään WebGL2-kaaviolle...`);
    const res = await chartManager.injectIndicator(code, name);
    if (res.success) {
      appendLog(`[Kaavio] Indikaattori "${name}" renderöity kaaviolle!`);
    } else {
      appendLog(`[Kaaviovirhe] Indikaattorin injektio epäonnistui: ${res.error}`);
    }
  };

  bridgeClient.onSummary = (text: string) => {
    if (agentSummary) {
      agentSummary.textContent = text;
    }
  };

  bridgeClient.onDone = () => {
    sendBtn.disabled = false;
    sendBtn.textContent = 'Aja';
  };

  bridgeClient.onConnectionChange = (connected: boolean, status: string) => {
    if (bridgeDot) {
      if (connected) {
        bridgeDot.classList.add('online');
      } else {
        bridgeDot.classList.remove('online');
      }
    }
    appendLog(`[Silta] ${status}`);
  };

  bridgeClient.connect();

  // 3. Prompt Submission Logic
  function handleSendPrompt() {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    const symbol = symbolSelect.value;
    const timeframe = timeframeSelect.value;
    const model = modelSelect.value;
    const effort = effortSelect.value;

    sendBtn.disabled = true;
    sendBtn.textContent = 'Ajetaan...';

    const sent = bridgeClient.sendPrompt(prompt, symbol, timeframe, model, effort);
    if (!sent) {
      sendBtn.disabled = false;
      sendBtn.textContent = 'Aja';
    }
  }

  sendBtn.addEventListener('click', handleSendPrompt);
  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      handleSendPrompt();
    }
  });

  // Preset chips click
  presetChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const p = chip.getAttribute('data-prompt');
      if (p) {
        promptInput.value = p;
        handleSendPrompt();
      }
    });
  });

  // Symbol and Timeframe selector changes
  symbolSelect.addEventListener('change', () => {
    const sym = symbolSelect.value;
    const tf = timeframeSelect.value;
    appendLog(`[Markkina] Vaihdetaan markkinapari: ${sym} (${tf})`);
    chartManager.setMarket(sym, tf);
  });

  timeframeSelect.addEventListener('change', () => {
    const sym = symbolSelect.value;
    const tf = timeframeSelect.value;
    appendLog(`[Aikajänne] Vaihdetaan aikajänne: ${tf} (${sym})`);
    chartManager.setMarket(sym, tf);
  });

  // Clear terminal
  if (clearTermBtn) {
    clearTermBtn.addEventListener('click', () => {
      terminal.innerHTML = '';
    });
  }
});
