/**
 * Application Entry Point: DOM controls, multi-indicator management,
 * TradingView community scripts library, historical data downloader, and live orchestrations.
 */

import { VelaChartManager, ActiveIndicatorItem } from './chart';
import { BridgeClient, BacktestMetrics, SavedIndicator } from './bridge_client';
import { COMMUNITY_SCRIPTS, CommunityScript } from './community_scripts';

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements - Main Controls
  const chartContainer = document.getElementById('chart-container') as HTMLElement;
  const promptInput = document.getElementById('prompt-input') as HTMLInputElement;
  const sendBtn = document.getElementById('send-btn') as HTMLButtonElement;
  const sourceSelect = document.getElementById('source-select') as HTMLSelectElement;
  const symbolSelect = document.getElementById('symbol-select') as HTMLSelectElement;
  const timeframeSelect = document.getElementById('timeframe-select') as HTMLSelectElement;
  const modelSelect = document.getElementById('model-select') as HTMLSelectElement;
  const modeSelect = document.getElementById('mode-select') as HTMLSelectElement;
  const bridgeDot = document.getElementById('bridge-status-dot') as HTMLElement;
  const hlDot = document.getElementById('hl-status-dot') as HTMLElement;
  const terminal = document.getElementById('agent-terminal') as HTMLElement;
  const clearTermBtn = document.getElementById('clear-term-btn') as HTMLButtonElement;
  const agentSummary = document.getElementById('agent-summary') as HTMLElement;
  const presetChips = document.querySelectorAll('.preset-chip');
  const quickAskBtns = document.querySelectorAll('.quick-ask-btn');
  const saveCurrentIndBtn = document.getElementById('save-current-ind-btn') as HTMLButtonElement;

  // Active indicators bar
  const activeIndicatorsList = document.getElementById('active-indicators-list') as HTMLElement;
  const clearAllIndicatorsBtn = document.getElementById('clear-all-indicators-btn') as HTMLButtonElement;

  // Header modal triggers
  const btnIndicatorsModal = document.getElementById('btn-indicators-modal') as HTMLButtonElement;
  const btnHistoricalModal = document.getElementById('btn-historical-modal') as HTMLButtonElement;
  const btnAskChart = document.getElementById('btn-ask-chart') as HTMLButtonElement;

  // Modals
  const indicatorsModal = document.getElementById('indicators-modal') as HTMLElement;
  const historicalModal = document.getElementById('historical-modal') as HTMLElement;

  // Indicators modal elements
  const tabSavedIndicators = document.getElementById('tab-saved-indicators') as HTMLElement;
  const tabCommunityScripts = document.getElementById('tab-community-scripts') as HTMLElement;
  const tabNewIndicator = document.getElementById('tab-new-indicator') as HTMLElement;
  const savedIndicatorsList = document.getElementById('saved-indicators-list') as HTMLElement;
  const communityScriptsList = document.getElementById('community-scripts-list') as HTMLElement;
  const csSearchInput = document.getElementById('cs-search-input') as HTMLInputElement;
  const csCategorySelect = document.getElementById('cs-category-select') as HTMLSelectElement;
  const newIndName = document.getElementById('new-ind-name') as HTMLInputElement;
  const newIndDesc = document.getElementById('new-ind-desc') as HTMLInputElement;
  const newIndCode = document.getElementById('new-ind-code') as HTMLTextAreaElement;
  const btnSaveNewInd = document.getElementById('btn-save-new-ind') as HTMLButtonElement;

  // Historical downloader elements
  const histSymbol = document.getElementById('hist-symbol') as HTMLInputElement;
  const histTimeframe = document.getElementById('hist-timeframe') as HTMLSelectElement;
  const histStartYear = document.getElementById('hist-start-year') as HTMLInputElement;
  const histStartMonth = document.getElementById('hist-start-month') as HTMLInputElement;
  const histEndMonth = document.getElementById('hist-end-month') as HTMLInputElement;
  const btnRunHistoricalDownload = document.getElementById('btn-run-historical-download') as HTMLButtonElement;
  const histDownloadStatus = document.getElementById('hist-download-status') as HTMLElement;
  const downloadedArchivesList = document.getElementById('downloaded-archives-list') as HTMLElement;

  // Metrics elements
  const metricWinrate = document.getElementById('metric-winrate') as HTMLElement;
  const metricPf = document.getElementById('metric-pf') as HTMLElement;
  const metricDd = document.getElementById('metric-dd') as HTMLElement;
  const metricTrades = document.getElementById('metric-trades') as HTMLElement;
  const metricAvgret = document.getElementById('metric-avgret') as HTMLElement;
  const metricTotret = document.getElementById('metric-totret') as HTMLElement;

  // State
  let lastInjectedCode = '';
  let lastInjectedName = '';

  function appendLog(message: string) {
    if (!terminal) return;
    const line = document.createElement('div');
    line.className = 'terminal-line';

    if (message.includes('[Virhe]') || message.includes('error') || message.includes('Error')) {
      line.classList.add('error');
    } else if (message.includes('[Validointi]') || message.includes('onnistuneesti') || message.includes('OK') || message.includes('Renderöity')) {
      line.classList.add('success');
    } else if (message.includes('[Järjestelmä]') || message.includes('[Bridge]') || message.includes('[Kuvaaja-analyysi]')) {
      line.classList.add('info');
    } else if (message.includes('[Korjaus]') || message.includes('[Varoitus]')) {
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
  const initialSource = sourceSelect?.value || 'hyperliquid';
  const initialSymbol = symbolSelect.value || 'BTC';
  const initialTimeframe = timeframeSelect.value || '1h';
  const chartManager = new VelaChartManager(chartContainer);

  try {
    chartManager.init(initialSymbol, initialTimeframe, initialSource);
    if (hlDot) {
      hlDot.classList.add('online');
    }
    appendLog(`[Järjestelmä] Vela WebGL2 -kaavio alustettu: ${initialSource.toUpperCase()} ${initialSymbol} (${initialTimeframe}).`);
  } catch (err) {
    appendLog(`[Virhe] Vela-kaavion alustus epäonnistui: ${err}`);
  }

  // Multi-indicator active bar update listener
  chartManager.onActiveIndicatorsChange = (indicators: ActiveIndicatorItem[]) => {
    renderActiveIndicatorsBar(indicators);
  };

  function renderActiveIndicatorsBar(indicators: ActiveIndicatorItem[]) {
    if (!activeIndicatorsList) return;
    activeIndicatorsList.innerHTML = '';

    if (indicators.length === 0) {
      activeIndicatorsList.innerHTML = '<span class="no-indicators-hint">Ei aktiivisia indikaattoreita (avaa kirjasto 📊 Indikaattorit)</span>';
      return;
    }

    indicators.forEach((ind) => {
      const chip = document.createElement('div');
      chip.className = `active-indicator-chip ${ind.visible ? '' : 'hidden-chip'}`;
      chip.setAttribute('data-id', ind.id);

      const title = document.createElement('span');
      title.textContent = ind.name;

      const toggleBtn = document.createElement('button');
      toggleBtn.className = 'chip-action-btn';
      toggleBtn.title = ind.visible ? 'Piilota indikaattori' : 'Näytä indikaattori';
      toggleBtn.textContent = ind.visible ? '👁️' : '🙈';
      toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        chartManager.toggleIndicatorVisibility(ind.id);
      });

      const removeBtn = document.createElement('button');
      removeBtn.className = 'chip-action-btn';
      removeBtn.title = 'Poista indikaattori kaaviolta';
      removeBtn.textContent = '✕';
      removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        chartManager.removeIndicator(ind.id);
        appendLog(`[Kaavio] Poistettu indikaattori "${ind.name}" kaaviolta.`);
      });

      chip.appendChild(toggleBtn);
      chip.appendChild(title);
      chip.appendChild(removeBtn);
      activeIndicatorsList.appendChild(chip);
    });
  }

  if (clearAllIndicatorsBtn) {
    clearAllIndicatorsBtn.addEventListener('click', () => {
      chartManager.clearAllIndicators();
      appendLog('[Kaavio] Kaikki aktiiviset indikaattorit poistettu ruudulta.');
    });
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
    lastInjectedCode = code;
    lastInjectedName = name;
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
      agentSummary.innerHTML = formatMarkdownText(text);
    }
  };

  bridgeClient.onChartAnalysis = (analysis) => {
    if (agentSummary) {
      agentSummary.innerHTML = formatMarkdownText(analysis.text);
    }
    appendLog('[Kuvaaja-analyysi] Tilannearvio valmistunut!');
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

  function formatMarkdownText(md: string): string {
    return md
      .replace(/### (.*?)\n/g, '<h4 style="margin:6px 0 4px 0; color:#60a5fa;">$1</h4>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n- (.*?)/g, '<br>• $1')
      .replace(/\n\n/g, '<br><br>');
  }

  // 3. Prompt Submission Logic
  function handleSendPrompt() {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    const source = sourceSelect ? sourceSelect.value : 'hyperliquid';
    const symbol = symbolSelect.value;
    const timeframe = timeframeSelect.value;
    const model = modelSelect.value;
    const mode = modeSelect ? modeSelect.value : 'auto';

    sendBtn.disabled = true;
    sendBtn.textContent = 'Ajetaan...';

    const sent = bridgeClient.sendPrompt(prompt, symbol, timeframe, model, 'high', mode, source);
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

  // 4. "Kysy kuvaajasta" - Chart technical analysis handler
  function handleAskChart(questionText?: string) {
    const q = questionText || promptInput.value.trim() || 'Mikä on tämänhetkinen tilanne? Onko osto vai myynti?';
    const model = modelSelect.value;
    const mode = modeSelect ? modeSelect.value : 'auto';
    const snapshot = chartManager.getChartContextSnapshot();

    appendLog(`[Kysy kuvaajasta] Haetaan tilannearvio kysymykselle: "${q}"...`);
    if (agentSummary) {
      agentSummary.textContent = 'Analysoidaan kuvaajan tilannetta ja aktiivisia indikaattoreita...';
    }

    sendBtn.disabled = true;
    sendBtn.textContent = 'Analysoidaan...';

    bridgeClient.askAboutChart(q, snapshot, model, 'high', mode);
  }

  if (btnAskChart) {
    btnAskChart.addEventListener('click', () => handleAskChart());
  }

  quickAskBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const q = btn.getAttribute('data-question') || '';
      handleAskChart(q);
    });
  });

  // Source, Symbol and Timeframe selector changes
  if (sourceSelect) {
    sourceSelect.addEventListener('change', () => {
      const src = sourceSelect.value;
      const sym = symbolSelect.value;
      const tf = timeframeSelect.value;
      appendLog(`[Datalähde] Vaihdetaan pörssi: ${src.toUpperCase()} (${sym} ${tf})`);
      chartManager.setMarket(sym, tf, src);
    });
  }

  symbolSelect.addEventListener('change', () => {
    const sym = symbolSelect.value;
    const tf = timeframeSelect.value;
    const src = sourceSelect ? sourceSelect.value : 'hyperliquid';
    appendLog(`[Markkina] Vaihdetaan markkinapari: ${src.toUpperCase()}:${sym} (${tf})`);
    chartManager.setMarket(sym, tf, src);
  });

  timeframeSelect.addEventListener('change', () => {
    const sym = symbolSelect.value;
    const tf = timeframeSelect.value;
    const src = sourceSelect ? sourceSelect.value : 'hyperliquid';
    appendLog(`[Aikajänne] Vaihdetaan aikajänne: ${tf} (${src.toUpperCase()}:${sym})`);
    chartManager.setMarket(sym, tf, src);
  });

  // Clear terminal
  if (clearTermBtn) {
    clearTermBtn.addEventListener('click', () => {
      terminal.innerHTML = '';
    });
  }

  // 5. Modals Management (Open / Close)
  function openModal(modal: HTMLElement) {
    modal.classList.add('open');
  }

  function closeModal(modal: HTMLElement) {
    modal.classList.remove('open');
  }

  document.querySelectorAll('[data-close]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-close');
      if (targetId) {
        const modal = document.getElementById(targetId);
        if (modal) closeModal(modal);
      }
    });
  });

  // Close modal when clicking outside window
  [indicatorsModal, historicalModal].forEach((m) => {
    if (m) {
      m.addEventListener('click', (e) => {
        if (e.target === m) closeModal(m);
      });
    }
  });

  if (btnIndicatorsModal) {
    btnIndicatorsModal.addEventListener('click', () => {
      openModal(indicatorsModal);
      loadSavedIndicators();
      renderCommunityScripts();
    });
  }

  if (btnHistoricalModal) {
    btnHistoricalModal.addEventListener('click', () => {
      openModal(historicalModal);
      loadHistoricalArchives();
    });
  }

  // 6. Indicators Library Tabs
  const modalTabBtns = document.querySelectorAll('.modal-tab-btn');
  modalTabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      modalTabBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      if (tabSavedIndicators) tabSavedIndicators.style.display = targetTab === 'tab-saved-indicators' ? 'block' : 'none';
      if (tabCommunityScripts) tabCommunityScripts.style.display = targetTab === 'tab-community-scripts' ? 'block' : 'none';
      if (tabNewIndicator) tabNewIndicator.style.display = targetTab === 'tab-new-indicator' ? 'block' : 'none';
    });
  });

  // 7. Community Scripts Library Rendering
  function renderCommunityScripts() {
    if (!communityScriptsList) return;
    const filterText = (csSearchInput?.value || '').toLowerCase().trim();
    const filterCategory = csCategorySelect?.value || 'all';

    const filtered = COMMUNITY_SCRIPTS.filter((s) => {
      const matchCat = filterCategory === 'all' || s.category === filterCategory;
      const matchText = !filterText || s.name.toLowerCase().includes(filterText) || s.description.toLowerCase().includes(filterText) || s.author.toLowerCase().includes(filterText);
      return matchCat && matchText;
    });

    communityScriptsList.innerHTML = '';
    filtered.forEach((script) => {
      const card = document.createElement('div');
      card.className = 'script-card';

      card.innerHTML = `
        <div class="script-card-header">
          <span class="script-name">${script.name}</span>
          <span class="script-tag">${script.category}</span>
        </div>
        <div class="script-author">Tekijä: ${script.author} | ${script.overlay ? 'Hintapeitto (Overlay)' : 'Oma alapaneeli'}</div>
        <div class="script-desc">${script.description}</div>
        <div class="script-actions">
          <button class="btn-xs btn-outline btn-view-code">Koodi</button>
          <button class="btn-xs btn-primary btn-inject-script">+ Lisää kaavioon</button>
        </div>
      `;

      card.querySelector('.btn-inject-script')?.addEventListener('click', async () => {
        appendLog(`[Kirjasto] Injektoidaan "${script.name}" kaaviolle...`);
        const res = await chartManager.injectIndicator(script.code, script.name);
        if (res.success) {
          appendLog(`[Kirjasto] "${script.name}" aktivoitu kaaviolla!`);
          closeModal(indicatorsModal);
        } else {
          appendLog(`[Virhe] Indikaattorin injektio epäonnistui: ${res.error}`);
        }
      });

      card.querySelector('.btn-view-code')?.addEventListener('click', () => {
        if (promptInput) promptInput.value = `// ${script.name}\n${script.code}`;
        appendLog(`[Kirjasto] "${script.name}" koodi ladattu komentoriville.`);
        closeModal(indicatorsModal);
      });

      communityScriptsList.appendChild(card);
    });
  }

  if (csSearchInput) csSearchInput.addEventListener('input', renderCommunityScripts);
  if (csCategorySelect) csCategorySelect.addEventListener('change', renderCommunityScripts);

  // 8. Saved Indicators Loading & Storage
  async function loadSavedIndicators() {
    if (!savedIndicatorsList) return;
    savedIndicatorsList.innerHTML = '<div style="color:#64748b;">Ladataan...</div>';

    const indicators = await bridgeClient.getIndicators();
    savedIndicatorsList.innerHTML = '';

    if (indicators.length === 0) {
      savedIndicatorsList.innerHTML = '<div style="color:#64748b; font-style:italic;">Ei vielä omia tallennettuja indikaattoreita. Voit luoda sellaisen tekoälyllä tai tallentaa nykyisen kaaviokoodin!</div>';
      return;
    }

    indicators.forEach((ind: SavedIndicator) => {
      const card = document.createElement('div');
      card.className = 'script-card';

      card.innerHTML = `
        <div class="script-card-header">
          <span class="script-name">${ind.name}</span>
          <span class="script-tag">${ind.category || 'Omat'}</span>
        </div>
        <div class="script-desc">${ind.description || 'Ei kuvausta'}</div>
        <div class="script-actions">
          <button class="btn-xs btn-danger btn-delete-ind">Poista</button>
          <button class="btn-xs btn-primary btn-apply-ind">+ Lisää kaavioon</button>
        </div>
      `;

      card.querySelector('.btn-apply-ind')?.addEventListener('click', async () => {
        appendLog(`[Omat indikaattorit] Injektoidaan "${ind.name}" kaaviolle...`);
        const res = await chartManager.injectIndicator(ind.code, ind.name);
        if (res.success) {
          appendLog(`[Omat indikaattorit] "${ind.name}" lisätty kaaviolle!`);
          closeModal(indicatorsModal);
        } else {
          appendLog(`[Virhe] Injektio epäonnistui: ${res.error}`);
        }
      });

      card.querySelector('.btn-delete-ind')?.addEventListener('click', async () => {
        if (confirm(`Haluatko varmasti poistaa indikaattorin "${ind.name}"?`)) {
          await bridgeClient.deleteIndicator(ind.id);
          appendLog(`[Omat indikaattorit] Poistettu "${ind.name}".`);
          loadSavedIndicators();
        }
      });

      savedIndicatorsList.appendChild(card);
    });
  }

  // Save new indicator form
  if (btnSaveNewInd) {
    btnSaveNewInd.addEventListener('click', async () => {
      const name = newIndName?.value.trim();
      const desc = newIndDesc?.value.trim();
      const code = newIndCode?.value.trim();

      if (!name || !code) {
        alert('Anna indikaattorille vähintään nimi ja koodi.');
        return;
      }

      const saved = await bridgeClient.saveIndicator({
        name,
        description: desc,
        code,
        category: 'Omat',
        author: 'Käyttäjä',
      });

      if (saved) {
        appendLog(`[Kirjasto] Tallennettu indikaattori "${name}".`);
        if (newIndName) newIndName.value = '';
        if (newIndDesc) newIndDesc.value = '';
        if (newIndCode) newIndCode.value = '';
        // Switch to saved tab
        const savedTabBtn = document.querySelector('[data-tab="tab-saved-indicators"]') as HTMLElement;
        if (savedTabBtn) savedTabBtn.click();
        loadSavedIndicators();
      }
    });
  }

  // "Tallenna nykyinen indikaattori" quick button
  if (saveCurrentIndBtn) {
    saveCurrentIndBtn.addEventListener('click', () => {
      openModal(indicatorsModal);
      const newTabBtn = document.querySelector('[data-tab="tab-new-indicator"]') as HTMLElement;
      if (newTabBtn) newTabBtn.click();
      if (newIndName) newIndName.value = lastInjectedName || 'Oma indikaattori';
      if (newIndCode) newIndCode.value = lastInjectedCode || '';
    });
  }

  // 9. Historical Data Downloader Logic
  async function loadHistoricalArchives() {
    if (!downloadedArchivesList) return;
    downloadedArchivesList.innerHTML = '<span style="color:#64748b;">Ladataan arkistolistausta...</span>';

    const data = await bridgeClient.getHistoricalArchives();
    const archives = data.archives || [];

    if (archives.length === 0) {
      downloadedArchivesList.innerHTML = '<span style="color:#64748b; font-style:italic;">Ei ladattuja arkistoja levyllä vielä. Valitse ylhäältä pari ja kuukausi ja paina "Lataa ja pura arkisto".</span>';
      return;
    }

    let html = '<table style="width:100%; border-collapse:collapse; text-align:left;">';
    html += '<tr style="border-bottom:1px solid #334155; color:#94a3b8;"><th>Pari</th><th>Aikaväli</th><th>Kuukausi</th><th>Koko</th><th>Tiedosto</th></tr>';
    archives.forEach((a: any) => {
      html += `<tr style="border-bottom:1px solid #1e293b; padding:4px 0;">
        <td style="color:#60a5fa; font-weight:600;">${a.symbol}</td>
        <td>${a.interval}</td>
        <td>${a.month}</td>
        <td>${a.size_kb} kt</td>
        <td style="color:#94a3b8; font-family:monospace; font-size:0.75rem;">${a.filename}</td>
      </tr>`;
    });
    html += '</table>';
    downloadedArchivesList.innerHTML = html;
  }

  if (btnRunHistoricalDownload) {
    btnRunHistoricalDownload.addEventListener('click', async () => {
      const symbol = histSymbol?.value.trim() || 'BTCUSDT';
      const interval = histTimeframe?.value || '1h';
      const start_year = parseInt(histStartYear?.value || '2024', 10);
      const start_month = parseInt(histStartMonth?.value || '1', 10);
      const end_month = parseInt(histEndMonth?.value || '1', 10);

      btnRunHistoricalDownload.disabled = true;
      if (histDownloadStatus) histDownloadStatus.textContent = 'Ladataan data.binance.vision -palvelimelta...';
      appendLog(`[Historiadata] Aloitetaan lataus: ${symbol} ${interval} (${start_year} kk ${start_month} - ${end_month})...`);

      const res = await bridgeClient.downloadHistorical({
        symbol,
        interval,
        start_year,
        start_month,
        end_year: start_year,
        end_month,
      });

      btnRunHistoricalDownload.disabled = false;
      if (res && res.status === 'ok') {
        const details = res.result || {};
        const successCount = details.successful_months || 0;
        const totalRows = details.total_rows || 0;
        if (histDownloadStatus) histDownloadStatus.textContent = `Valmis! Ladattu ${successCount} kuukautta (${totalRows} kynttilää).`;
        appendLog(`[Historiadata] Onnistui! Ladattu ${successCount} kuukautta (${totalRows} riviä CSV:nä levylle).`);
        loadHistoricalArchives();
      } else {
        if (histDownloadStatus) histDownloadStatus.textContent = `Latausvirhe: ${res.error || 'Tuntematon virhe'}`;
        appendLog(`[Virhe] Historiadatan lataus epäonnistui: ${res.error || 'Tuntematon virhe'}`);
      }
    });
  }
});
