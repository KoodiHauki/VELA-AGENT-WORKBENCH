/**
 * Application Entry Point: DOM controls, multi-indicator management,
 * TradingView community scripts library, historical data downloader,
 * full token pair search & favorites bar, and chart analysis chat.
 */

import { VelaChartManager, ActiveIndicatorItem } from './chart';
import { BridgeClient, BacktestMetrics, SavedIndicator, TradingSymbol } from './bridge_client';
import { COMMUNITY_SCRIPTS } from './community_scripts';

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
  const saveCurrentIndBtn = document.getElementById('save-current-ind-btn') as HTMLButtonElement;

  // Dedicated chart analysis response card elements
  const chartAnalysisCard = document.getElementById('chart-analysis-card') as HTMLElement;
  const chartAnalysisOutput = document.getElementById('chart-analysis-output') as HTMLElement;
  const analysisBiasBadge = document.getElementById('analysis-bias-badge') as HTMLElement;
  const analysisTimestamp = document.getElementById('analysis-timestamp') as HTMLElement;
  const copyAnalysisBtn = document.getElementById('copy-analysis-btn') as HTMLButtonElement;
  const closeAnalysisBtn = document.getElementById('close-analysis-btn') as HTMLButtonElement;

  // Active indicators bar
  const activeIndicatorsList = document.getElementById('active-indicators-list') as HTMLElement;
  const clearAllIndicatorsBtn = document.getElementById('clear-all-indicators-btn') as HTMLButtonElement;

  // Header market picker & favorites bar
  const btnSymbolPicker = document.getElementById('btn-symbol-picker') as HTMLButtonElement;
  const currentSymbolDisplay = document.getElementById('current-symbol-display') as HTMLElement;
  const currentSourceBadge = document.getElementById('current-source-badge') as HTMLElement;
  const favoritesList = document.getElementById('favorites-list') as HTMLElement;
  const btnAddFavorite = document.getElementById('btn-add-favorite') as HTMLButtonElement;

  // Header modal triggers
  const btnIndicatorsModal = document.getElementById('btn-indicators-modal') as HTMLButtonElement;
  const btnHistoricalModal = document.getElementById('btn-historical-modal') as HTMLButtonElement;
  const btnAskChart = document.getElementById('btn-ask-chart') as HTMLButtonElement;

  // Modals
  const indicatorsModal = document.getElementById('indicators-modal') as HTMLElement;
  const historicalModal = document.getElementById('historical-modal') as HTMLElement;
  const symbolModal = document.getElementById('symbol-modal') as HTMLElement;

  // Symbol modal elements
  const symbolSearchInput = document.getElementById('symbol-search-input') as HTMLInputElement;
  const symbolGridList = document.getElementById('symbol-grid-list') as HTMLElement;
  const favCountBadge = document.getElementById('fav-count-badge') as HTMLElement;
  const symbolFilterBtns = document.querySelectorAll('.symbol-filter-btn');

  // Indicators modal elements
  const tabSavedIndicators = document.getElementById('tab-saved-indicators') as HTMLElement;
  const tabCommunityScripts = document.getElementById('tab-community-scripts') as HTMLElement;
  const tabNewIndicator = document.getElementById('tab-new-indicator') as HTMLElement;
  const savedIndicatorsList = document.getElementById('saved-indicators-list') as HTMLElement;
  const communityScriptsList = document.getElementById('community-scripts-list') as HTMLElement;
  const csSearchInput = document.getElementById('cs-search-input') as HTMLInputElement;
  const csCategorySelect = document.getElementById('cs-category-select') as HTMLSelectElement;

  // Subtabs inside New Indicator modal
  const btnSubtabAi = document.getElementById('btn-subtab-ai') as HTMLButtonElement;
  const btnSubtabManual = document.getElementById('btn-subtab-manual') as HTMLButtonElement;
  const subtabAiGenerator = document.getElementById('subtab-ai-generator') as HTMLElement;
  const subtabManualCode = document.getElementById('subtab-manual-code') as HTMLElement;
  const aiIndPrompt = document.getElementById('ai-ind-prompt') as HTMLTextAreaElement;
  const aiIndModel = document.getElementById('ai-ind-model') as HTMLSelectElement;
  const aiIndMode = document.getElementById('ai-ind-mode') as HTMLSelectElement;
  const btnRunAiIndicator = document.getElementById('btn-run-ai-indicator') as HTMLButtonElement;
  const aiIndResultCode = document.getElementById('ai-ind-result-code') as HTMLTextAreaElement;
  const aiIndStatus = document.getElementById('ai-ind-status') as HTMLElement;
  const btnAiApplyInd = document.getElementById('btn-ai-apply-ind') as HTMLButtonElement;
  const btnAiSaveInd = document.getElementById('btn-ai-save-ind') as HTMLButtonElement;
  const aiPromptChips = document.querySelectorAll('.ai-prompt-chip');

  // Manual indicator editor
  const newIndName = document.getElementById('new-ind-name') as HTMLInputElement;
  const newIndDesc = document.getElementById('new-ind-desc') as HTMLInputElement;
  const newIndCode = document.getElementById('new-ind-code') as HTMLTextAreaElement;
  const btnTestNewInd = document.getElementById('btn-test-new-ind') as HTMLButtonElement;
  const btnSaveNewInd = document.getElementById('btn-save-new-ind') as HTMLButtonElement;

  // Historical downloader elements
  const histSymbol = document.getElementById('hist-symbol') as HTMLInputElement;
  const histTimeframe = document.getElementById('hist-timeframe') as HTMLSelectElement;
  const histStartYear = document.getElementById('hist-start-year') as HTMLInputElement;
  const histStartMonth = document.getElementById('hist-start-month') as HTMLInputElement;
  const histEndYear = document.getElementById('hist-end-year') as HTMLInputElement;
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

  // App State
  let lastInjectedCode = '';
  let lastInjectedName = '';
  let currentSymbol = 'BTC';
  let currentSource = 'hyperliquid';
  let currentPairName = 'BTC/USD';
  let allSymbols: TradingSymbol[] = [];
  let favoriteKeys: Set<string> = loadFavorites();
  let activeSymbolFilter: string = 'all';

  function loadFavorites(): Set<string> {
    try {
      const stored = localStorage.getItem('vela_favorite_pairs');
      if (stored) {
        return new Set(JSON.parse(stored));
      }
    } catch (_) {}
    return new Set(['hyperliquid:BTC', 'hyperliquid:ETH', 'hyperliquid:SOL', 'binance:BTCUSDT']);
  }

  function saveFavorites() {
    try {
      localStorage.setItem('vela_favorite_pairs', JSON.stringify(Array.from(favoriteKeys)));
    } catch (_) {}
    if (favCountBadge) {
      favCountBadge.textContent = String(favoriteKeys.size);
    }
  }

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
  currentSource = sourceSelect?.value || 'hyperliquid';
  currentSymbol = symbolSelect?.value || 'BTC';
  const initialTimeframe = timeframeSelect?.value || '1h';
  const chartManager = new VelaChartManager(chartContainer);

  try {
    chartManager.init(currentSymbol, initialTimeframe, currentSource);
    if (hlDot) {
      hlDot.classList.add('online');
    }
    appendLog(`[Järjestelmä] Vela WebGL2 -kaavio alustettu: ${currentSource.toUpperCase()} ${currentSymbol} (${initialTimeframe}).`);
  } catch (err) {
    appendLog(`[Virhe] Vela-kaavion alustus epäonnistui: ${err}`);
  }

  // Multi-indicator active bar listener
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

    // Populate AI generator editor in modal if open
    if (aiIndResultCode) aiIndResultCode.value = code;
    if (btnAiApplyInd) btnAiApplyInd.style.display = 'inline-block';
    if (btnAiSaveInd) btnAiSaveInd.style.display = 'inline-block';
    if (aiIndStatus) aiIndStatus.textContent = `Generointi valmis! (${name})`;

    appendLog(`[Kaavio] Vastaanotettu indikaattori "${name}". Piirretään WebGL2-kaaviolle...`);
    const res = await chartManager.injectIndicator(code, name);
    if (res.success) {
      appendLog(`[Kaavio] Indikaattori "${name}" renderöity kaaviolle!`);
    } else {
      appendLog(`[Kaaviovirhe] Indikaattorin injektio epäonnistui: ${res.error}`);
    }
  };

  let currentAnalysisText = '';

  bridgeClient.onSummary = (text: string) => {
    if (agentSummary) {
      agentSummary.innerHTML = formatMarkdownText(text);
    }
  };

  bridgeClient.onChartAnalysisChunk = (delta: string) => {
    if (!currentAnalysisText) {
      // Clear loading placeholder on first chunk
      if (chartAnalysisOutput) {
        chartAnalysisOutput.innerHTML = '';
      }
    }
    currentAnalysisText += delta;
    if (chartAnalysisOutput) {
      chartAnalysisOutput.innerHTML = formatMarkdownText(currentAnalysisText);
    }
  };

  bridgeClient.onChartAnalysis = (analysis) => {
    currentAnalysisText = analysis.text;
    if (chartAnalysisOutput) {
      chartAnalysisOutput.innerHTML = formatMarkdownText(analysis.text);
    }

    if (analysisBiasBadge) {
      analysisBiasBadge.className = 'analysis-badge';
      const b = (analysis.bias || '').toUpperCase();
      const txt = (analysis.text || '').toUpperCase();
      if (b === 'BUY' || txt.includes('🟢 OSTO') || txt.includes('BUY')) {
        analysisBiasBadge.classList.add('badge-buy');
        analysisBiasBadge.textContent = '🟢 OSTO';
      } else if (b === 'SELL' || txt.includes('🔴 MYYNTI') || txt.includes('SELL')) {
        analysisBiasBadge.classList.add('badge-sell');
        analysisBiasBadge.textContent = '🔴 MYYNTI';
      } else {
        analysisBiasBadge.classList.add('badge-neutral');
        analysisBiasBadge.textContent = '🟡 NEUTRAALI';
      }
    }

    if (analysisTimestamp) {
      analysisTimestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    appendLog('[Kuvaaja-analyysi] Tekninen tilannearvio valmistunut!');
  };

  bridgeClient.onDone = () => {
    sendBtn.disabled = false;
    sendBtn.textContent = 'Kysy';
    if (btnRunAiIndicator) {
      btnRunAiIndicator.disabled = false;
      btnRunAiIndicator.textContent = '🚀 Generoi indikaattori';
    }
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
    if (connected) {
      loadSymbols();
    }
  };

  bridgeClient.connect();

  function formatMarkdownText(md: string): string {
    return md
      .replace(/### (.*?)\n/g, '<h4 style="margin:6px 0 4px 0; color:#60a5fa;">$1</h4>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n- (.*?)/g, '<br>• $1')
      .replace(/\n\n/g, '<br><br>');
  }

  // 3. Market Selection and Switching
  function selectMarket(symbol: string, timeframe?: string, source?: string, displayName?: string) {
    currentSymbol = symbol.trim();
    if (source) currentSource = source.toLowerCase();
    const tf = timeframe || timeframeSelect?.value || '1h';

    // Synchronize select controls
    if (sourceSelect) sourceSelect.value = currentSource;
    if (symbolSelect) {
      let opt = Array.from(symbolSelect.options).find((o) => o.value === currentSymbol);
      if (!opt) {
        opt = new Option(currentSymbol, currentSymbol);
        symbolSelect.add(opt);
      }
      symbolSelect.value = currentSymbol;
    }
    if (timeframe && timeframeSelect) {
      timeframeSelect.value = timeframe;
    }

    currentPairName = displayName || (currentSource === 'binance' ? `${currentSymbol.replace('USDT', '')}/USDT` : `${currentSymbol}/USD`);
    if (currentSymbolDisplay) {
      currentSymbolDisplay.textContent = currentPairName;
    }
    if (currentSourceBadge) {
      if (currentSource === 'hyperliquid') {
        currentSourceBadge.textContent = 'HL';
        currentSourceBadge.className = 'source-mini-badge hl';
      } else if (currentSource === 'binance') {
        currentSourceBadge.textContent = 'BINANCE';
        currentSourceBadge.className = 'source-mini-badge bi';
      } else {
        currentSourceBadge.textContent = 'ARKISTO';
        currentSourceBadge.className = 'source-mini-badge';
      }
    }

    appendLog(`[Markkina] Vaihdetaan markkinapari: ${currentSource.toUpperCase()}:${currentSymbol} (${tf})`);
    chartManager.setMarket(currentSymbol, tf, currentSource);
    renderFavoritesBar();
  }

  // 4. Token Pairs & Favorites Management
  async function loadSymbols() {
    try {
      allSymbols = await bridgeClient.getSymbols('all');
      saveFavorites();
      renderFavoritesBar();
      renderSymbolGridList();
    } catch (e) {
      console.warn('Failed to load symbols:', e);
    }
  }

  function toggleFavorite(key: string, e?: Event) {
    if (e) e.stopPropagation();
    if (favoriteKeys.has(key)) {
      favoriteKeys.delete(key);
      appendLog(`[Suosikit] Poistettu suosikeista: ${key}`);
    } else {
      favoriteKeys.add(key);
      appendLog(`[Suosikit] Lisätty suosikiksi: ${key}`);
    }
    saveFavorites();
    renderFavoritesBar();
    renderSymbolGridList();
  }

  function renderFavoritesBar() {
    if (!favoritesList) return;
    favoritesList.innerHTML = '';

    if (favoriteKeys.size === 0) {
      favoritesList.innerHTML = '<span style="color:#64748b; font-style:italic;">Ei suosikkeja. Klikkaa tähteä ⭐ lisätäksesi.</span>';
      return;
    }

    favoriteKeys.forEach((key) => {
      const parts = key.split(':');
      const src = parts[0];
      const sym = parts[1];
      const matched = allSymbols.find((s) => s.source === src && s.symbol === sym);
      const label = matched ? matched.pair : `${sym}/${src === 'binance' ? 'USDT' : 'USD'}`;
      const isActive = currentSymbol === sym && currentSource === src;

      const chip = document.createElement('div');
      chip.className = `favorite-chip ${isActive ? 'active' : ''}`;
      chip.innerHTML = `
        <span>⭐ ${label}</span>
        <span class="fav-remove-btn" title="Poista suosikeista">&times;</span>
      `;

      chip.addEventListener('click', () => {
        selectMarket(sym, timeframeSelect?.value || '1h', src, label);
      });

      chip.querySelector('.fav-remove-btn')?.addEventListener('click', (e) => {
        toggleFavorite(key, e);
      });

      favoritesList.appendChild(chip);
    });
  }

  function renderSymbolGridList() {
    if (!symbolGridList) return;
    const query = (symbolSearchInput?.value || '').trim().toLowerCase();

    const filtered = allSymbols.filter((s) => {
      const key = `${s.source}:${s.symbol}`;
      if (activeSymbolFilter === 'favorites' && !favoriteKeys.has(key)) return false;
      if (activeSymbolFilter === 'hyperliquid' && s.source !== 'hyperliquid') return false;
      if (activeSymbolFilter === 'binance' && s.source !== 'binance') return false;

      if (!query) return true;
      return (
        s.symbol.toLowerCase().includes(query) ||
        s.pair.toLowerCase().includes(query) ||
        s.base.toLowerCase().includes(query)
      );
    });

    symbolGridList.innerHTML = '';
    if (filtered.length === 0) {
      symbolGridList.innerHTML = '<div style="color:#64748b; font-style:italic; padding:12px;">Ei hakuehtoja vastaavia tokeneita tai pareja.</div>';
      return;
    }

    // Render up to 100 rows for high rendering performance
    filtered.slice(0, 100).forEach((s) => {
      const key = `${s.source}:${s.symbol}`;
      const isStarred = favoriteKeys.has(key);
      const isActive = currentSymbol === s.symbol && currentSource === s.source;

      const row = document.createElement('div');
      row.className = `symbol-row ${isActive ? 'active' : ''}`;
      row.innerHTML = `
        <div class="symbol-row-left">
          <button class="symbol-star-btn ${isStarred ? 'starred' : ''}" title="${isStarred ? 'Poista suosikeista' : 'Lisää suosikkeihin'}">
            ${isStarred ? '★' : '☆'}
          </button>
          <span class="symbol-pair-name">${s.pair}</span>
          <span class="symbol-base-badge">${s.base}</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          ${s.maxLeverage ? `<span style="font-size:0.7rem; color:#64748b;">${s.maxLeverage}x</span>` : ''}
          <span class="symbol-source-badge ${s.source === 'hyperliquid' ? 'hl' : 'bi'}">${s.source === 'hyperliquid' ? 'HL' : 'Binance'}</span>
        </div>
      `;

      row.querySelector('.symbol-star-btn')?.addEventListener('click', (e) => {
        toggleFavorite(key, e);
      });

      row.addEventListener('click', () => {
        selectMarket(s.symbol, timeframeSelect?.value || '1h', s.source, s.pair);
        closeModal(symbolModal);
      });

      symbolGridList.appendChild(row);
    });
  }

  // Symbol modal search & filter triggers
  if (btnSymbolPicker) {
    btnSymbolPicker.addEventListener('click', () => {
      openModal(symbolModal);
      if (symbolSearchInput) {
        symbolSearchInput.value = '';
        symbolSearchInput.focus();
      }
      renderSymbolGridList();
    });
  }

  if (symbolSearchInput) {
    symbolSearchInput.addEventListener('input', () => {
      renderSymbolGridList();
    });
  }

  symbolFilterBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      symbolFilterBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      activeSymbolFilter = btn.getAttribute('data-filter') || 'all';
      renderSymbolGridList();
    });
  });

  if (btnAddFavorite) {
    btnAddFavorite.addEventListener('click', () => {
      const key = `${currentSource}:${currentSymbol}`;
      toggleFavorite(key);
    });
  }

  // 5. Right Sidebar: Dedicated "Kysy kuvaajasta"
  function handleAskChart(questionText?: string) {
    const q = questionText || promptInput.value.trim() || 'Mikä on tämänhetkinen tilanne? Onko osto vai myynti?';
    promptInput.value = q;
    const model = modelSelect.value;
    const mode = modeSelect ? modeSelect.value : 'auto';
    const snapshot = chartManager.getChartContextSnapshot();

    currentAnalysisText = '';

    // Show dedicated analysis card immediately right below the prompt & chips
    if (chartAnalysisCard) {
      chartAnalysisCard.style.display = 'block';
    }

    if (analysisBiasBadge) {
      analysisBiasBadge.className = 'analysis-badge badge-neutral';
      analysisBiasBadge.textContent = '🟡 ANALYSOIDAAN...';
    }

    if (analysisTimestamp) {
      analysisTimestamp.textContent = '';
    }

    if (chartAnalysisOutput) {
      chartAnalysisOutput.innerHTML = `
        <div class="analysis-loading-box">
          <div class="analysis-pulse-dot"></div>
          <span>Analysoidaan kuvaajan teknistä tilannetta, indikaattoreita ja avaintasoja...</span>
        </div>
      `;
    }

    appendLog(`[Kysy kuvaajasta] Haetaan tilannearvio kysymykselle: "${q}"...`);

    sendBtn.disabled = true;
    sendBtn.textContent = 'Analysoidaan...';

    // Scroll analysis card into view so user sees it right away
    if (chartAnalysisCard) {
      chartAnalysisCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    bridgeClient.askAboutChart(q, snapshot, model, 'high', mode);
  }

  sendBtn.addEventListener('click', () => handleAskChart());
  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      handleAskChart();
    }
  });

  if (btnAskChart) {
    btnAskChart.addEventListener('click', () => {
      promptInput.focus();
      handleAskChart();
    });
  }

  presetChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const q = chip.getAttribute('data-question');
      if (q) {
        promptInput.value = q;
        handleAskChart(q);
      }
    });
  });

  // Copy analysis button
  if (copyAnalysisBtn) {
    copyAnalysisBtn.addEventListener('click', async () => {
      if (currentAnalysisText) {
        try {
          await navigator.clipboard.writeText(currentAnalysisText);
          const origText = copyAnalysisBtn.textContent;
          copyAnalysisBtn.textContent = 'Kopioitu! ✔️';
          setTimeout(() => {
            copyAnalysisBtn.textContent = origText;
          }, 2000);
        } catch (e) {
          appendLog(`[Leikepöytä] Kopiointivirhe: ${e}`);
        }
      }
    });
  }

  // Close analysis card button
  if (closeAnalysisBtn) {
    closeAnalysisBtn.addEventListener('click', () => {
      if (chartAnalysisCard) {
        chartAnalysisCard.style.display = 'none';
      }
    });
  }

  // Source and Timeframe dropdown changes
  if (sourceSelect) {
    sourceSelect.addEventListener('change', () => {
      const src = sourceSelect.value;
      if (src === 'archive') {
        openModal(historicalModal);
        loadHistoricalArchives();
        return;
      }
      selectMarket(currentSymbol, timeframeSelect.value, src);
    });
  }

  timeframeSelect.addEventListener('change', () => {
    const tf = timeframeSelect.value;
    appendLog(`[Aikajänne] Vaihdetaan aikajänne: ${tf} (${currentSource.toUpperCase()}:${currentSymbol})`);
    chartManager.setMarket(currentSymbol, tf, currentSource);
  });

  // Clear terminal
  if (clearTermBtn) {
    clearTermBtn.addEventListener('click', () => {
      terminal.innerHTML = '';
    });
  }

  // 6. Modals Management (Open / Close)
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

  [indicatorsModal, historicalModal, symbolModal].forEach((m) => {
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

  // Mobile section jump navigation buttons
  document.querySelectorAll('.mobile-nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      if (targetId) {
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  });


  // 7. Indicators Library Modal Logic
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

  // Subtabs inside Tab 3: New Indicator
  if (btnSubtabAi && btnSubtabManual) {
    btnSubtabAi.addEventListener('click', () => {
      btnSubtabAi.classList.add('active');
      btnSubtabManual.classList.remove('active');
      if (subtabAiGenerator) subtabAiGenerator.style.display = 'block';
      if (subtabManualCode) subtabManualCode.style.display = 'none';
    });

    btnSubtabManual.addEventListener('click', () => {
      btnSubtabManual.classList.add('active');
      btnSubtabAi.classList.remove('active');
      if (subtabManualCode) subtabManualCode.style.display = 'block';
      if (subtabAiGenerator) subtabAiGenerator.style.display = 'none';
    });
  }

  // AI prompt template chips
  aiPromptChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const p = chip.getAttribute('data-prompt');
      if (p && aiIndPrompt) {
        aiIndPrompt.value = p;
      }
    });
  });

  // Run AI Indicator Generator
  if (btnRunAiIndicator) {
    btnRunAiIndicator.addEventListener('click', () => {
      const prompt = aiIndPrompt?.value.trim();
      if (!prompt) {
        alert('Kirjoita indikaattoripyyntö ennen ajamista.');
        return;
      }

      btnRunAiIndicator.disabled = true;
      btnRunAiIndicator.textContent = 'Generoidaan tekoälyllä...';
      if (aiIndStatus) aiIndStatus.textContent = 'Lähetetään pyyntö Antigravity-moottorille...';

      const model = aiIndModel?.value || 'gemini-3.8-flash-high';
      const mode = aiIndMode?.value || 'auto';
      const tf = timeframeSelect?.value || '1h';

      appendLog(`[Tekoäly] Aloitetaan uuden indikaattorin luonti: "${prompt}"...`);
      bridgeClient.sendPrompt(prompt, currentSymbol, tf, model, 'high', mode, currentSource);
    });
  }

  // Apply AI generated indicator to chart
  if (btnAiApplyInd) {
    btnAiApplyInd.addEventListener('click', async () => {
      const code = aiIndResultCode?.value.trim();
      if (!code) return;
      appendLog(`[Kirjasto] Lisätään generoitu koodi kaavioon...`);
      const res = await chartManager.injectIndicator(code, lastInjectedName || 'AI Indicator');
      if (res.success) {
        appendLog(`[Kirjasto] Indikaattori aktivoitu kaaviolla!`);
        closeModal(indicatorsModal);
      } else {
        appendLog(`[Virhe] Indikaattorin lisäys epäonnistui: ${res.error}`);
      }
    });
  }

  // Save AI generated indicator to library
  if (btnAiSaveInd) {
    btnAiSaveInd.addEventListener('click', async () => {
      const code = aiIndResultCode?.value.trim();
      if (!code) return;
      const name = prompt('Anna indikaattorille nimi:', lastInjectedName || 'Uusi tekoälyindikaattori') || lastInjectedName;
      if (!name) return;

      const saved = await bridgeClient.saveIndicator({
        name,
        description: aiIndPrompt?.value || 'Tekoälyn generoima Pine Script v5 -indikaattori',
        code,
        category: 'Tekoäly',
        author: 'Antigravity AI',
      });

      if (saved) {
        appendLog(`[Kirjasto] Tallennettu indikaattori "${name}" kirjastoon.`);
        const savedTabBtn = document.querySelector('[data-tab="tab-saved-indicators"]') as HTMLElement;
        if (savedTabBtn) savedTabBtn.click();
        loadSavedIndicators();
      }
    });
  }

  // Manual indicator buttons
  if (btnTestNewInd) {
    btnTestNewInd.addEventListener('click', async () => {
      const code = newIndCode?.value.trim();
      const name = newIndName?.value.trim() || 'Oma indikaattori';
      if (!code) {
        alert('Liitä tai kirjoita Pine Script v5 -koodi.');
        return;
      }
      appendLog(`[Manuaalinen] Testataan koodia kaaviolla...`);
      const res = await chartManager.injectIndicator(code, name);
      if (res.success) {
        appendLog(`[Manuaalinen] Indikaattori "${name}" aktivoitu kaaviolla!`);
        closeModal(indicatorsModal);
      } else {
        appendLog(`[Virhe] Injektio epäonnistui: ${res.error}`);
      }
    });
  }

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
        const savedTabBtn = document.querySelector('[data-tab="tab-saved-indicators"]') as HTMLElement;
        if (savedTabBtn) savedTabBtn.click();
        loadSavedIndicators();
      }
    });
  }

  // Quick save current indicator button
  if (saveCurrentIndBtn) {
    saveCurrentIndBtn.addEventListener('click', () => {
      openModal(indicatorsModal);
      const newTabBtn = document.querySelector('[data-tab="tab-new-indicator"]') as HTMLElement;
      if (newTabBtn) newTabBtn.click();
      if (btnSubtabManual) btnSubtabManual.click();
      if (newIndName) newIndName.value = lastInjectedName || 'Oma indikaattori';
      if (newIndCode) newIndCode.value = lastInjectedCode || '';
    });
  }

  // 8. Community Scripts Rendering
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

  // 9. Saved Indicators List Rendering
  async function loadSavedIndicators() {
    if (!savedIndicatorsList) return;
    savedIndicatorsList.innerHTML = '<div style="color:#64748b;">Ladataan tallennettuja...</div>';

    const indicators = await bridgeClient.getIndicators();
    savedIndicatorsList.innerHTML = '';

    if (indicators.length === 0) {
      savedIndicatorsList.innerHTML = '<div style="color:#64748b; font-style:italic;">Ei vielä omia tallennettuja indikaattoreita. Voit luoda uuden "+ Uusi indikaattori" -välilehdellä!</div>';
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

  // 10. Historical Data Downloader & Archive Chart Display
  async function loadHistoricalArchives() {
    if (!downloadedArchivesList) return;
    downloadedArchivesList.innerHTML = '<span style="color:#64748b;">Ladataan arkistolistausta...</span>';

    const data = await bridgeClient.getHistoricalArchives();
    const archives = data.archives || [];

    if (archives.length === 0) {
      downloadedArchivesList.innerHTML = '<span style="color:#64748b; font-style:italic;">Ei ladattuja arkistoja levyllä vielä. Valitse ylhäältä aikajänne ja kuukaudet ja paina "Lataa ja pura arkisto".</span>';
      return;
    }

    let html = '<table style="width:100%; border-collapse:collapse; text-align:left;">';
    html += '<tr style="border-bottom:1px solid #334155; color:#94a3b8;"><th>Pari</th><th>Aikaväli</th><th>Kuukausi</th><th>Koko</th><th>Tiedosto</th><th style="text-align:right;">Toiminto</th></tr>';
    archives.forEach((a: any) => {
      html += `<tr style="border-bottom:1px solid #1e293b; padding:6px 0;">
        <td style="color:#60a5fa; font-weight:600;">${a.symbol}</td>
        <td>${a.interval}</td>
        <td>${a.month}</td>
        <td>${a.size_kb} kt</td>
        <td style="color:#94a3b8; font-family:monospace; font-size:0.75rem;">${a.filename}</td>
        <td style="text-align:right;">
          <button class="btn-xs btn-primary btn-open-archive" data-file="${a.filename}" data-symbol="${a.symbol}" data-interval="${a.interval}">📊 Avaa kaaviolla</button>
        </td>
      </tr>`;
    });
    html += '</table>';
    downloadedArchivesList.innerHTML = html;

    // Attach click listeners to open archive in chart
    downloadedArchivesList.querySelectorAll('.btn-open-archive').forEach((btn) => {
      btn.addEventListener('click', () => {
        const file = btn.getAttribute('data-file') || '';
        const sym = btn.getAttribute('data-symbol') || '';
        const interval = btn.getAttribute('data-interval') || '1h';
        appendLog(`[Historiadata] Avataan paikallinen arkisto kaaviolle: ${file} (${interval})...`);
        selectMarket(file, interval, 'archive', `${sym} (Arkisto)`);
        closeModal(historicalModal);
      });
    });
  }

  if (btnRunHistoricalDownload) {
    btnRunHistoricalDownload.addEventListener('click', async () => {
      const symbol = histSymbol?.value.trim() || 'BTCUSDT';
      const interval = histTimeframe?.value || '1h';
      const start_year = parseInt(histStartYear?.value || '2024', 10);
      const start_month = parseInt(histStartMonth?.value || '1', 10);
      const end_year = parseInt(histEndYear?.value || String(start_year), 10);
      const end_month = parseInt(histEndMonth?.value || '3', 10);

      btnRunHistoricalDownload.disabled = true;
      if (histDownloadStatus) histDownloadStatus.textContent = 'Ladataan data.binance.vision -palvelimelta...';
      appendLog(`[Historiadata] Aloitetaan lataus: ${symbol} ${interval} (${start_year}/${start_month} - ${end_year}/${end_month})...`);

      const res = await bridgeClient.downloadHistorical({
        symbol,
        interval,
        start_year,
        start_month,
        end_year,
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
